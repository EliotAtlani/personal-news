#!/usr/bin/env python3
"""
Preview the newsletter template with fake data
"""

from jinja2 import Template
from datetime import datetime
import webbrowser
import os
import tempfile

def create_fake_data():
    """Generate realistic fake data for the newsletter template"""
    
    fake_data = {
        'newsletter_title': 'Your Daily Tech Digest',
        'current_date': datetime.now().strftime('%B %d, %Y'),
        'total_articles': 12,
        'summary': 'Today\'s tech news includes major AI breakthroughs, cybersecurity updates, and significant moves in the startup ecosystem. Notable highlights include OpenAI\'s new multimodal capabilities, a major data breach affecting millions of users, and record-breaking funding rounds in the fintech sector.',
        'user_email': 'user@example.com',
        'categories': {
            'Artificial Intelligence': [
                {
                    'article': {
                        'title': 'OpenAI Unveils Revolutionary Multimodal AI Assistant',
                        'url': 'https://example.com/openai-multimodal-ai',
                        'source': 'TechCrunch'
                    },
                    'brief_summary': 'OpenAI has announced a breakthrough in multimodal AI that can seamlessly process text, images, audio, and video simultaneously. The new model demonstrates unprecedented understanding across different media types, potentially revolutionizing how we interact with AI systems.',
                    'importance_score': 9.2,
                    'key_points': [
                        'Processes multiple media types simultaneously',
                        'Shows 40% improvement in cross-modal understanding',
                        'Expected to be integrated into ChatGPT by Q2 2024',
                        'Could impact video editing, content creation, and education sectors'
                    ]
                },
                {
                    'article': {
                        'title': 'Google\'s Gemini AI Shows Promise in Medical Diagnosis',
                        'url': 'https://example.com/gemini-medical-diagnosis',
                        'source': 'Nature Medicine'
                    },
                    'brief_summary': 'Recent studies show Google\'s Gemini AI model achieving 94% accuracy in diagnosing rare diseases from patient symptoms and medical imaging. The breakthrough could significantly improve healthcare outcomes in underserved regions.',
                    'importance_score': 8.7,
                    'key_points': [
                        '94% accuracy in rare disease diagnosis',
                        'Tested on over 50,000 medical cases',
                        'Particularly effective with dermatological conditions',
                        'Partnership with WHO for global deployment being discussed'
                    ]
                }
            ],
            'Cybersecurity': [
                {
                    'article': {
                        'title': 'Major Banking Trojan Discovered Targeting Mobile Wallets',
                        'url': 'https://example.com/banking-trojan-mobile',
                        'source': 'Security Week'
                    },
                    'brief_summary': 'Cybersecurity researchers have identified a sophisticated new banking trojan specifically designed to steal credentials from popular mobile payment apps. The malware has already affected over 100,000 devices across 15 countries.',
                    'importance_score': 8.9,
                    'key_points': [
                        'Targets popular mobile payment apps like Venmo, PayPal, and Cash App',
                        'Uses advanced screen overlay techniques to steal credentials',
                        'Distributed through malicious apps on third-party stores',
                        'Security patches released for affected platforms'
                    ]
                },
                {
                    'article': {
                        'title': 'Zero-Day Vulnerability Found in Popular VPN Software',
                        'url': 'https://example.com/vpn-zero-day',
                        'source': 'The Hacker News'
                    },
                    'brief_summary': 'A critical zero-day vulnerability has been discovered in NordVPN and ExpressVPN clients that could allow attackers to bypass VPN protections and intercept user traffic. Both companies have released emergency patches.',
                    'importance_score': 8.1,
                    'key_points': [
                        'Affects over 50 million VPN users globally',
                        'Could expose real IP addresses despite active VPN connection',
                        'Exploitation requires local network access',
                        'Emergency patches available for immediate download'
                    ]
                }
            ],
            'Startups & Venture Capital': [
                {
                    'article': {
                        'title': 'Climate Tech Startup Raises $200M Series B for Carbon Capture',
                        'url': 'https://example.com/climate-tech-series-b',
                        'source': 'PitchBook'
                    },
                    'brief_summary': 'CarbonVault, a promising climate technology startup, has secured $200 million in Series B funding to scale their direct air capture technology. The round was led by Breakthrough Energy Ventures with participation from major institutional investors.',
                    'importance_score': 7.8,
                    'key_points': [
                        'Breakthrough Energy Ventures leads $200M Series B round',
                        'Technology can capture 1,000 tons of CO2 per day per facility',
                        'Plans to build 50 facilities across North America by 2027',
                        'Could create permanent storage for 18 million tons of CO2 annually'
                    ]
                },
                {
                    'article': {
                        'title': 'Fintech Unicorn Acquired by JPMorgan for $12B',
                        'url': 'https://example.com/fintech-acquisition',
                        'source': 'Wall Street Journal'
                    },
                    'brief_summary': 'JPMorgan Chase has announced the acquisition of PayFlow, a fintech unicorn specializing in small business lending, for $12 billion. This marks the largest fintech acquisition by a traditional bank in 2024.',
                    'importance_score': 8.4,
                    'key_points': [
                        'Largest fintech acquisition by traditional bank in 2024',
                        'PayFlow serves over 2 million small businesses',
                        'Integration expected to be completed within 18 months',
                        'Will enhance JPMorgan\'s digital lending capabilities significantly'
                    ]
                }
            ],
            'Science & Space': [
                {
                    'article': {
                        'title': 'NASA\'s Artemis III Mission Delayed to Late 2025',
                        'url': 'https://example.com/artemis-delay',
                        'source': 'Space News'
                    },
                    'brief_summary': 'NASA has officially announced a delay to the Artemis III lunar landing mission, pushing the timeline from 2024 to late 2025. The delay is attributed to technical challenges with the new spacesuits and lunar lander development.',
                    'importance_score': 7.3,
                    'key_points': [
                        'Mission delayed by approximately 12 months',
                        'Spacesuit development facing technical hurdles',
                        'Lunar lander requires additional testing and validation',
                        'Artemis II orbital mission still on track for late 2024'
                    ]
                }
            ]
        }
    }
    
    return fake_data

def preview_template():
    """Load the template and render it with fake data"""
    
    # Read the template
    template_path = '/Users/eliotatlani/Developer/portefolio/personal-news/templates/newsletter.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Create Jinja2 template
    template = Template(template_content)
    
    # Generate fake data
    fake_data = create_fake_data()
    
    # Render template
    rendered_html = template.render(**fake_data)
    
    # Save to temporary file and open in browser
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(rendered_html)
        temp_file_path = f.name
    
    print(f"Template rendered successfully!")
    print(f"Preview file created at: {temp_file_path}")
    print("Opening in default browser...")
    
    # Open in browser
    webbrowser.open(f'file://{temp_file_path}')
    
    return temp_file_path

if __name__ == "__main__":
    preview_template()