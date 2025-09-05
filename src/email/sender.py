import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import jinja2
from src.ai.summarizer import ArticleSummary
from src.config.manager import Config

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, config: Config):
        self.config = config
        self.template_loader = jinja2.FileSystemLoader(
            Path(__file__).parent.parent.parent / "templates"
        )
        self.template_env = jinja2.Environment(loader=self.template_loader)
    
    def create_newsletter_content(self, summaries: List[ArticleSummary], 
                                categories: Dict[str, List[ArticleSummary]]) -> tuple[str, str]:
        """Create HTML and plain text content for the newsletter."""
        try:
            # Load HTML template
            template = self.template_env.get_template('newsletter.html')
            
            # Create overall summary
            overall_summary = self._create_overall_summary(summaries)
            
            # Render HTML content
            html_content = template.render(
                newsletter_title="Daily News Digest",
                current_date=datetime.now().strftime("%B %d, %Y"),
                total_articles=len(summaries),
                summary=overall_summary,
                categories=categories,
                user_email=self.config.user.email
            )
            
            # Create plain text version
            plain_content = self._create_plain_text_content(summaries, categories, overall_summary)
            
            return html_content, plain_content
            
        except Exception as e:
            logger.error(f"Error creating newsletter content: {e}")
            # Fallback to simple text
            return self._create_fallback_content(summaries), self._create_fallback_content(summaries)
    
    def _create_overall_summary(self, summaries: List[ArticleSummary]) -> str:
        """Create an overall summary of the day's news."""
        if not summaries:
            return "No articles found matching your interests today."
        
        # Count articles by category
        categories = {}
        total_importance = 0
        
        for summary in summaries:
            category = summary.category
            categories[category] = categories.get(category, 0) + 1
            total_importance += summary.importance_score
        
        # Create summary text
        avg_importance = total_importance / len(summaries) if summaries else 0
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary_parts = [
            f"Today's digest includes {len(summaries)} articles"
        ]
        
        if top_categories:
            category_text = ", ".join([f"{count} {cat.lower()}" for cat, count in top_categories])
            summary_parts.append(f"covering mainly {category_text}")
        
        if avg_importance > 0.7:
            summary_parts.append("Several high-importance stories require your attention.")
        elif avg_importance > 0.5:
            summary_parts.append("Mixed importance levels with some notable developments.")
        else:
            summary_parts.append("Generally lower-impact news today.")
        
        return " ".join(summary_parts)
    
    def _create_plain_text_content(self, summaries: List[ArticleSummary], 
                                 categories: Dict[str, List[ArticleSummary]], 
                                 overall_summary: str) -> str:
        """Create plain text version of the newsletter."""
        content = []
        content.append("=" * 60)
        content.append("DAILY NEWS DIGEST")
        content.append(f"{datetime.now().strftime('%B %d, %Y')} • {len(summaries)} articles")
        content.append("=" * 60)
        content.append("")
        
        if overall_summary:
            content.append("TODAY'S HIGHLIGHTS")
            content.append("-" * 20)
            content.append(overall_summary)
            content.append("")
        
        if not categories:
            content.append("No articles found matching your interests today.")
            content.append("")
        
        for category, articles in categories.items():
            content.append(f"{category.upper()}")
            content.append("-" * len(category))
            content.append("")
            
            for i, summary in enumerate(articles, 1):
                content.append(f"{i}. {summary.article.title}")
                content.append(f"   Source: {summary.article.source} | Score: {summary.importance_score:.1f}")
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
    
    def _create_fallback_content(self, summaries: List[ArticleSummary]) -> str:
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
    
    def send_newsletter(self, summaries: List[ArticleSummary], 
                       categories: Dict[str, List[ArticleSummary]]) -> bool:
        """Send the newsletter email."""
        try:
            # Create email content
            html_content, plain_content = self.create_newsletter_content(summaries, categories)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily News Digest - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.config.email.sender_email
            msg['To'] = self.config.user.email
            
            # Add plain text and HTML parts
            plain_part = MIMEText(plain_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
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
            with smtplib.SMTP(self.config.email.smtp_server, self.config.email.smtp_port) as server:
                server.starttls()  # Enable security
                server.login(self.config.email.sender_email, self.config.email.sender_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(self.config.email.sender_email, self.config.user.email, text)
                
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
            msg['Subject'] = "Personal News - Test Email"
            msg['From'] = self.config.email.sender_email
            msg['To'] = self.config.user.email
            
            body = """
            This is a test email from your Personal News system.
            
            If you received this, your email configuration is working correctly!
            
            Configuration details:
            - SMTP Server: {}
            - SMTP Port: {}
            - Sender: {}
            - Recipient: {}
            
            You can now set up your daily news digest.
            """.format(
                self.config.email.smtp_server,
                self.config.email.smtp_port,
                self.config.email.sender_email,
                self.config.user.email
            )
            
            msg.attach(MIMEText(body, 'plain'))
            
            return self._send_email(msg)
            
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return False
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send an error notification email."""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = "Personal News - Error Occurred"
            msg['From'] = self.config.email.sender_email
            msg['To'] = self.config.user.email
            
            body = f"""
            An error occurred while generating your daily news digest:
            
            Error: {error_message}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please check your configuration and try again.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            return self._send_email(msg)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False