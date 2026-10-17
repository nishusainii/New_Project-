#!/usr/bin/env python3
"""
Gmail Inbox Audit & Management Tool
Analyzes emails to separate useful emails from spam, marketing, and automated junk.
Uses standard Python libraries (imaplib, email).
"""

import imaplib
import email
from email.header import decode_header
import re
from collections import Counter
import getpass
import os
import html

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def clean_header(header_value):
    if not header_value:
        return ""
    decoded_list = decode_header(header_value)
    result = []
    for text, encoding in decoded_list:
        if isinstance(text, bytes):
            try:
                result.append(text.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                result.append(text.decode("latin1", errors="replace"))
        else:
            result.append(str(text))
    return "".join(result)

def extract_email(from_str):
    match = re.search(r'<([^>]+)>', from_str)
    if match:
        return match.group(1).lower()
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_str)
    if match:
        return match.group(0).lower()
    return from_str.lower()

def categorize_email(from_addr, subject, has_unsubscribe, headers):
    subj_lower = subject.lower()
    from_lower = from_addr.lower()

    # 1. Marketing / Promotional
    if has_unsubscribe or any(k in from_lower for k in ['promo', 'news', 'info@', 'marketing', 'deals', 'no-reply', 'noreply']):
        if any(k in subj_lower for k in ['otp', 'verify', 'security alert', 'invoice', 'receipt', 'bill']):
            return 'Transactional (Important)'
        return 'Promotions / Newsletters'

    # 2. Transactional / Security / Financial
    if any(k in subj_lower for k in ['otp', 'verification code', 'security alert', 'password reset', 'bank', 'statement', 'invoice', 'payment']):
        return 'Transactional (Important)'

    # 3. Social Media Notifications
    if any(k in from_lower for k in ['facebook', 'linkedin', 'twitter', 'instagram', 'youtube', 'pinterest', 'tiktok']):
        return 'Social Media'

    # 4. Likely Genuine / Personal
    return 'Personal / Direct Email'

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gmail Inbox Audit & Management Tool")
    parser.add_argument("--email", "-e", help="Gmail address (default: rameshsaini217@gmail.com)", default="")
    parser.add_argument("--password", "-p", help="16-letter Google App Password", default="")
    parser.add_argument("--limit", "-l", type=int, help="Number of recent emails to analyze", default=100)
    args = parser.parse_args()

    print("=" * 65)
    print(" Gmail Inbox Audit & Management Tool")
    print("=" * 65)
    
    default_email = "rameshsaini217@gmail.com"
    if args.email:
        email_user = args.email.strip()
    else:
        email_user = input(f"Enter Gmail address [{default_email}]: ").strip() or default_email
    
    if args.password:
        app_password = args.password.strip().replace(" ", "")
    else:
        print("\nNote: Use the 16-letter Google App Password (not your regular password).")
        app_password = getpass.getpass("Enter 16-letter App Password: ").strip().replace(" ", "")
    
    if not app_password:
        print("[-] Password cannot be empty.")
        return

    print(f"\n[+] Connecting to {IMAP_SERVER}...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email_user, app_password)
        print("[✔] Successfully authenticated with Gmail!")
    except Exception as e:
        print(f"[-] Authentication failed: {e}")
        print("\nTip: Make sure 2-Step Verification is ON and generate an App Password at:")
        print("     https://myaccount.google.com/apppasswords")
        return

    # Select Inbox
    mail.select("INBOX")
    
    # Ask for scan limit
    if args.password:
        limit = args.limit
    else:
        print("\nHow many recent emails would you like to analyze?")
        limit_str = input(f"Enter number (e.g. 100, 250, 500) [{args.limit}]: ").strip() or str(args.limit)
        limit = int(limit_str)

    print(f"\n[+] Scanning the last {limit} emails from INBOX...")
    status, messages = mail.search(None, "ALL")
    if status != "OK":
        print("[-] Failed to retrieve messages.")
        return

    mail_ids = messages[0].split()
    total_found = len(mail_ids)
    print(f"[✔] Total emails in INBOX: {total_found}")

    selected_ids = mail_ids[-limit:] if total_found > limit else mail_ids

    records = []
    sender_counter = Counter()
    category_counter = Counter()

    for idx, mid in enumerate(reversed(selected_ids), 1):
        try:
            _, msg_data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE LIST-UNSUBSCRIBE)])")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            from_raw = clean_header(msg.get("From", "Unknown"))
            subject_raw = clean_header(msg.get("Subject", "(No Subject)"))
            date_raw = clean_header(msg.get("Date", ""))
            unsub_header = msg.get("List-Unsubscribe")

            from_email = extract_email(from_raw)
            category = categorize_email(from_email, subject_raw, bool(unsub_header), msg)

            sender_counter[from_email] += 1
            category_counter[category] += 1

            records.append({
                "from_raw": from_raw,
                "from_email": from_email,
                "subject": subject_raw,
                "date": date_raw,
                "category": category,
                "has_unsub": bool(unsub_header)
            })

            if idx % 25 == 0 or idx == len(selected_ids):
                print(f"    Processed {idx}/{len(selected_ids)} emails...")
        except Exception as err:
            continue

    mail.close()
    mail.logout()

    # Terminal Summary
    print("\n" + "=" * 65)
    print(" INBOX AUDIT SUMMARY")
    print("=" * 65)
    for cat, count in category_counter.most_common():
        pct = (count / len(records)) * 100
        print(f" - {cat:<28}: {count:>3} emails ({pct:.1f}%)")

    print("\nTOP SENDER DOMAINS / ADDRESSES:")
    for s_email, count in sender_counter.most_common(8):
        print(f" - {s_email:<35}: {count} emails")

    # Generate HTML report
    html_path = os.path.join(os.path.dirname(__file__), "gmail_audit_report.html")
    generate_html_report(email_user, records, category_counter, sender_counter, html_path)
    print("\n[✔] Detailed Interactive Report generated at:")
    print(f"    {html_path}")
    print("    (You can double-click it to view in any web browser)")

def generate_html_report(user, records, category_counter, sender_counter, output_path):
    rows = []
    for r in records:
        cat_badge = {
            "Personal / Direct Email": '<span style="background:#dcfce7;color:#15803d;padding:3px 8px;border-radius:12px;font-weight:600;font-size:11px;">Useful / Personal</span>',
            "Transactional (Important)": '<span style="background:#e0f2fe;color:#0369a1;padding:3px 8px;border-radius:12px;font-weight:600;font-size:11px;">Transactional / OTP</span>',
            "Promotions / Newsletters": '<span style="background:#fee2e2;color:#b91c1c;padding:3px 8px;border-radius:12px;font-weight:600;font-size:11px;">Promo / Junk</span>',
            "Social Media": '<span style="background:#fef3c7;color:#b45309;padding:3px 8px;border-radius:12px;font-weight:600;font-size:11px;">Social Media</span>',
        }.get(r["category"], r["category"])

        rows.append(f"""<tr>
            <td><strong>{html.escape(r['from_raw'][:45])}</strong><br><small style="color:#64748b;">{html.escape(r['from_email'])}</small></td>
            <td>{html.escape(r['subject'][:70])}</td>
            <td>{cat_badge}</td>
            <td><small>{html.escape(r['date'][:22])}</small></td>
        </tr>""")

    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Gmail Inbox Audit - {user}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 25px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 20px; }}
  h1 {{ font-size: 20px; margin-top: 0; color: #0f172a; }}
  .grid {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat {{ background: #fff; padding: 15px 20px; border-radius: 8px; border-left: 4px solid #0284c7; flex: 1; min-width: 180px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .stat-val {{ font-size: 22px; font-weight: 700; margin-top: 5px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
  th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
  tr:hover {{ background: #f8fafc; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Gmail Audit Report for: <code>{user}</code></h1>
    <p style="color:#64748b;margin:0;">Analysis of recent emails to identify useful messages vs promotional spam.</p>
  </div>

  <div class="grid">
    <div class="stat" style="border-left-color: #10b981;">
      <div style="font-size:12px;color:#64748b;">USEFUL / PERSONAL</div>
      <div class="stat-val" style="color:#10b981;">{category_counter.get('Personal / Direct Email', 0)}</div>
    </div>
    <div class="stat" style="border-left-color: #0284c7;">
      <div style="font-size:12px;color:#64748b;">TRANSACTIONAL / OTP</div>
      <div class="stat-val" style="color:#0284c7;">{category_counter.get('Transactional (Important)', 0)}</div>
    </div>
    <div class="stat" style="border-left-color: #ef4444;">
      <div style="font-size:12px;color:#64748b;">PROMOTIONS / JUNK</div>
      <div class="stat-val" style="color:#ef4444;">{category_counter.get('Promotions / Newsletters', 0)}</div>
    </div>
    <div class="stat" style="border-left-color: #f59e0b;">
      <div style="font-size:12px;color:#64748b;">SOCIAL MEDIA</div>
      <div class="stat-val" style="color:#f59e0b;">{category_counter.get('Social Media', 0)}</div>
    </div>
  </div>

  <div class="card">
    <h2 style="font-size:16px;margin-top:0;">Analyzed Emails List</h2>
    <table>
      <thead>
        <tr>
          <th>Sender</th>
          <th>Subject</th>
          <th>Category</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
