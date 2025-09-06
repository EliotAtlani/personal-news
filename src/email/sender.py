import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import jinja2

from src.ai.summarizer import ArticleSummary
from src.config.manager import ProfileBasedConfig

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, config: ProfileBasedConfig):
        self.config = config
        self.template_loader = jinja2.FileSystemLoader(
            Path(__file__).parent.parent.parent / "templates"
        )
        self.template_env = jinja2.Environment(loader=self.template_loader)

    def create_newsletter_content(
        self,
        summaries: list[ArticleSummary],
        categories: dict[str, list[ArticleSummary]],
        profile: str = None,
    ) -> tuple[str, str]:
        """Create HTML and plain text content for the newsletter."""
        try:
            # Determine template name based on profile
            template_name = (
                f"{profile}-newsletter.html" if profile else "newsletter.html"
            )

            # Try to load profile-specific template, fallback to default
            try:
                template = self.template_env.get_template(template_name)
            except jinja2.TemplateNotFound:
                template = self.template_env.get_template("newsletter.html")

            # Create overall summary
            overall_summary = self._create_overall_summary(summaries, profile)

            # Get newsletter title based on profile
            newsletter_title = getattr(self.config, "name", "Newsletter")

            # Check if we have fewer articles than minimum
            insufficient_articles = len(summaries) < getattr(
                self.config.content, "min_articles", 2
            )

            # Render HTML content
            html_content = template.render(
                newsletter_title=newsletter_title,
                current_date=datetime.now().strftime("%B %d, %Y"),
                total_articles=len(summaries),
                summary=overall_summary,
                categories=categories,
                user_email=self.config.user.email,
                profile=profile,
                insufficient_articles=insufficient_articles,
                min_articles=getattr(self.config.content, "min_articles", 2),
            )

            # Create plain text version
            plain_content = self._create_plain_text_content(
                summaries, categories, overall_summary, profile
            )

            return html_content, plain_content

        except Exception as e:
            logger.error(f"Error creating newsletter content: {e}")
            # Fallback to simple text
            return self._create_fallback_content(
                summaries
            ), self._create_fallback_content(summaries)

    def _create_overall_summary(
        self, summaries: list[ArticleSummary], profile: str = None
    ) -> str:
        """Create an overall summary of the week's news."""
        if not summaries:
            min_articles = getattr(self.config.content, "min_articles", 2)
            return f"No articles found matching your interests this week. We typically aim for at least {min_articles} articles, but sources were limited."

        # Count articles by category
        categories = {}
        total_importance = 0

        for summary in summaries:
            category = summary.category
            categories[category] = categories.get(category, 0) + 1
            total_importance += summary.importance_score

        # Create summary text
        avg_importance = total_importance / len(summaries) if summaries else 0
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[
            :3
        ]

        # Get time period based on profile
        if profile:
            profile_name = getattr(self.config, "name", profile.title())
            summary_parts = [
                f"This week's {profile_name} digest includes {len(summaries)} articles"
            ]
        else:
            summary_parts = [f"This week's digest includes {len(summaries)} articles"]

        if top_categories:
            category_text = ", ".join(
                [f"{count} {cat.lower()}" for cat, count in top_categories]
            )
            summary_parts.append(f"covering mainly {category_text}")

        # Check if we have insufficient articles
        min_articles = getattr(self.config.content, "min_articles", 2)
        if len(summaries) < min_articles:
            summary_parts.append(
                f"Note: We found fewer articles than usual this week. We typically aim for {min_articles}+ articles but covered everything available."
            )

        if avg_importance > 0.7:
            summary_parts.append(
                "Several high-importance stories require your attention."
            )
        elif avg_importance > 0.5:
            summary_parts.append(
                "Mixed importance levels with some notable developments."
            )
        else:
            summary_parts.append("Generally lower-impact news this week.")

        return " ".join(summary_parts)

    def _create_plain_text_content(
        self,
        summaries: list[ArticleSummary],
        categories: dict[str, list[ArticleSummary]],
        overall_summary: str,
        profile: str = None,
    ) -> str:
        """Create plain text version of the newsletter."""
        content = []
        content.append("=" * 60)

        newsletter_title = getattr(self.config, "name", "NEWSLETTER").upper()
        content.append(newsletter_title)
        content.append(
            f"{datetime.now().strftime('%B %d, %Y')} • {len(summaries)} articles"
        )
        content.append("=" * 60)
        content.append("")

        if overall_summary:
            content.append("THIS WEEK'S HIGHLIGHTS")
            content.append("-" * 25)
            content.append(overall_summary)
            content.append("")

        if not categories:
            min_articles = getattr(self.config.content, "min_articles", 2)
            content.append("No articles found matching your interests this week.")
            content.append(
                f"We typically aim for at least {min_articles} articles, but sources were limited."
            )
            content.append("")

        for category, articles in categories.items():
            content.append(f"{category.upper()}")
            content.append("-" * len(category))
            content.append("")

            for i, summary in enumerate(articles, 1):
                content.append(f"{i}. {summary.article.title}")
                content.append(
                    f"   Source: {summary.article.source} | Score: {summary.importance_score:.1f}"
                )
                content.append(f"   {summary.brief_summary}")

                if summary.key_points:
                    content.append("   Key Points:")
                    for point in summary.key_points:
                        content.append(f"   • {point}")

                content.append(f"   Read more: {summary.article.url}")
                content.append("")

        content.append("-" * 60)
        content.append("Personal News Digest")
        content.append(f"Generated on {datetime.now().strftime('%B %d, %Y')}")
        content.append("-" * 60)

        return "\n".join(content)

    def _create_fallback_content(self, summaries: list[ArticleSummary]) -> str:
        """Create fallback content when template rendering fails."""
        content = [f"Daily News Digest - {datetime.now().strftime('%B %d, %Y')}"]
        content.append("=" * 50)

        if not summaries:
            content.append("No articles found today.")
            return "\n".join(content)

        for i, summary in enumerate(summaries, 1):
            content.append(f"\n{i}. {summary.article.title}")
            content.append(f"Source: {summary.article.source}")
            content.append(f"Summary: {summary.brief_summary}")
            content.append(f"Link: {summary.article.url}")

        return "\n".join(content)

    def send_newsletter(
        self,
        summaries: list[ArticleSummary],
        categories: dict[str, list[ArticleSummary]],
        profile: str = None,
    ) -> bool:
        """Send the newsletter email."""
        try:
            # Create email content
            html_content, plain_content = self.create_newsletter_content(
                summaries, categories, profile
            )

            # Create email message
            msg = MIMEMultipart("alternative")
            subject_prefix = getattr(self.config, "subject_prefix", "Newsletter")
            msg["Subject"] = (
                f"{subject_prefix} - {datetime.now().strftime('%B %d, %Y')}"
            )
            msg["From"] = self.config.email.sender_email
            msg["To"] = self.config.user.email

            # Add plain text and HTML parts
            plain_part = MIMEText(plain_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")

            msg.attach(plain_part)
            msg.attach(html_part)

            # Send email
            return self._send_email(msg)

        except Exception as e:
            logger.error(f"Error sending newsletter: {e}")
            return False

    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Send the email using SMTP."""
        try:
            # Create SMTP session
            with smtplib.SMTP(
                self.config.email.smtp_server, self.config.email.smtp_port
            ) as server:
                server.starttls()  # Enable security
                server.login(
                    self.config.email.sender_email, self.config.email.sender_password
                )

                # Send email
                text = msg.as_string()
                server.sendmail(
                    self.config.email.sender_email, self.config.user.email, text
                )

                logger.info(f"Newsletter sent successfully to {self.config.user.email}")
                return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            logger.error("Please check your email credentials and app password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False

    def send_test_email(self) -> bool:
        """Send a test email to verify configuration."""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = "Personal News - Test Email"
            msg["From"] = self.config.email.sender_email
            msg["To"] = self.config.user.email

            body = f"""
            This is a test email from your Personal News system.
            
            If you received this, your email configuration is working correctly!
            
            Configuration details:
            - SMTP Server: {self.config.email.smtp_server}
            - SMTP Port: {self.config.email.smtp_port}
            - Sender: {self.config.email.sender_email}
            - Recipient: {self.config.user.email}
            
            You can now set up your daily news digest.
            """

            msg.attach(MIMEText(body, "plain"))

            return self._send_email(msg)

        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return False

    def send_error_notification(self, error_message: str) -> bool:
        """Send an error notification email."""
        try:
            msg = MIMEMultipart()
            msg["Subject"] = "Personal News - Error Occurred"
            msg["From"] = self.config.email.sender_email
            msg["To"] = self.config.user.email

            body = f"""
            An error occurred while generating your daily news digest:
            
            Error: {error_message}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please check your configuration and try again.
            """

            msg.attach(MIMEText(body, "plain"))

            return self._send_email(msg)

        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
