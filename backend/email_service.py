import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from datetime import datetime

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

def is_valid_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return bool(re.match(EMAIL_REGEX, email))

def generate_digest_html(internships: list, recipient_email: str = "") -> str:
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    
    rows_html = ""
    for idx, item in enumerate(internships, start=1):
        score_badge = ""
        score = item.international_score or 5
        if score >= 8:
            score_badge = '<span style="background-color: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 700;">🌟 High F-1 Sponsor (Score: ' + str(score) + ')</span>'
        elif score >= 5:
            score_badge = '<span style="background-color: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 700;">🟢 CPT / OPT Friendly (Score: ' + str(score) + ')</span>'
        else:
            score_badge = '<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 700;">⚪ Citizen / PR Preferred (Score: ' + str(score) + ')</span>'

        ai_badge = ""
        if item.ai_label:
            ai_badge = '<span style="background-color: #f3e8ff; color: #7e22ce; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 700; margin-left: 6px;">🤖 GenAI / ML</span>'

        salary_text = f"💰 {item.salary}" if item.salary else "💰 Competitive Pay"
        company_logo = item.logo_url or f"https://ui-avatars.com/api/?name={item.company}&background=6366f1&color=fff"

        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 16px 12px; vertical-align: middle; width: 44px;">
            <div style="width: 42px; height: 42px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; display: flex; align-items: center; justify-content: center; text-align: center; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
              <img src="{company_logo}" alt="{item.company}" style="width: 32px; height: 32px; object-fit: contain; margin: 4px;" />
            </div>
          </td>
          <td style="padding: 16px 12px; vertical-align: top;">
            <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px; line-height: 1.3;">
              <a href="{item.url}" target="_blank" style="color: #2563eb; text-decoration: none;">{item.role}</a>
            </div>
            <div style="font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 6px;">
              🏢 {item.company} &nbsp;•&nbsp; 📍 {item.location} &nbsp;•&nbsp; {salary_text}
            </div>
            <div>
              {score_badge}
              {ai_badge}
            </div>
          </td>
          <td style="padding: 16px 12px; vertical-align: middle; text-align: right; white-space: nowrap;">
            <a href="{item.url}" target="_blank" style="background-color: #2563eb; color: #ffffff; font-size: 12px; font-weight: 700; text-decoration: none; padding: 8px 14px; border-radius: 8px; display: inline-block;">
              Apply Direct &rarr;
            </a>
          </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Internship Aggregator - Top 20 Daily Digest</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #334155;">
      <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); padding: 32px 24px; color: #ffffff; text-align: center;">
          <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 900; letter-spacing: -0.5px;">🎓 Internship Aggregator</h1>
          <p style="margin: 0; font-size: 15px; opacity: 0.95; font-weight: 600;">🔥 Top 20 Curated Internships Drop ({current_date})</p>
        </div>

        <!-- Info Bar -->
        <div style="background-color: #eff6ff; border-bottom: 1px solid #dbeafe; padding: 12px 24px; font-size: 13px; color: #1e40af; display: flex; justify-content: space-between; font-weight: 600;">
          <span>🎯 Handpicked for Tech, Quant & AI</span>
          <span>📅 Synced Daily • Direct Links</span>
        </div>

        <!-- Job Table -->
        <div style="padding: 8px 16px;">
          <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>

        <!-- Footer -->
        <div style="background-color: #f1f5f9; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
          <p style="margin: 0 0 8px 0;">You received this because you subscribed to the <strong>Internship Aggregator</strong> Daily Radar.</p>
          <p style="margin: 0;">🌐 Browse all 1,500+ active roles: <a href="https://internship-aggregator-nu.vercel.app" style="color: #2563eb; text-decoration: underline; font-weight: 600;">internship-aggregator-nu.vercel.app</a></p>
        </div>
      </div>
    </body>
    </html>
    """
    return html

def send_digest_email(recipient_email: str, internships: list) -> bool:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "noreply@internship-aggregator.com")

    if not smtp_host or not smtp_user or not smtp_pass:
        return False

    try:
        html_content = generate_digest_html(internships, recipient_email)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎓 [Daily Drop] Top 20 Tech & Finance Internships - Internship Aggregator"
        msg["From"] = f"Internship Aggregator <{smtp_from}>"
        msg["To"] = recipient_email

        part = MIMEText(html_content, "html")
        msg.attach(part)

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [recipient_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email via SMTP: {e}")
        return False
