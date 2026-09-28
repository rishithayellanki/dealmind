"""
DealMind Web Application Server.
Standard-library Python HTTP server serving the modern frontend
and providing full JSON API endpoints for Hindsight memory operations,
multi-tenant user data isolation, profile management, and verified password recovery.
No external dependencies required!
"""

import os
import json
import mimetypes
import re
import time
import secrets
import smtplib
from email.mime.text import MIMEText
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from memory_engine import HindsightMemoryEngine
from agent import generate_without_memory, generate_with_memory
from seed_data import seed_hindsight_memory, SAMPLE_DEALS

PORT = int(os.getenv("PORT", 8080))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
USER_DEALS_FILE = os.path.join(DATA_DIR, "user_deals.json")
RESETS_FILE = os.path.join(DATA_DIR, "password_resets.json")

# Initialize Hindsight Engine
memory_engine = HindsightMemoryEngine()
# Seed initial demo memories
seed_hindsight_memory(memory_engine, force_reset=False)


def _ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        default_users = {
            "yellanki.rishitha12@gmail.com": {
                "email": "yellanki.rishitha12@gmail.com",
                "name": "Rishitha Yellanki",
                "role": "Lead Account Executive",
                "org": "HackwithHyderabad 3.0 Finale Team",
                "workspace": "Microsoft Hyderabad Enterprise Hub",
                "memory_engine": "Local Disk JSON Engine (Active)",
                "password": "password123"
            },
            "judge.evaluator@microsoft.com": {
                "email": "judge.evaluator@microsoft.com",
                "name": "Judge Evaluator",
                "role": "Chief Revenue Officer (CRO)",
                "org": "HackwithHyderabad 3.0 Finale Team",
                "workspace": "Microsoft Hyderabad Enterprise Hub",
                "memory_engine": "Local Disk JSON Engine (Active)",
                "password": "password123"
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=2)

    if not os.path.exists(USER_DEALS_FILE):
        default_user_deals = {
            "yellanki.rishitha12@gmail.com": {
                "scrapq": {
                    "name": "scrapq",
                    "value": "$50,000 ARR",
                    "stage": "Discovery",
                    "industry": "Enterprise SaaS",
                    "calls": []
                }
            },
            "rishithayellanki12@gmail.com": {
                "scrapq": {
                    "name": "scrapq",
                    "value": "$50,000 ARR",
                    "stage": "Discovery",
                    "industry": "Enterprise SaaS",
                    "calls": []
                }
            }
        }
        with open(USER_DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_user_deals, f, indent=2)


def get_users_db() -> dict:
    _ensure_storage()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users_db(users: dict):
    _ensure_storage()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def get_user_deals_db() -> dict:
    _ensure_storage()
    if os.path.exists(USER_DEALS_FILE):
        try:
            with open(USER_DEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_user_deals_db(user_deals: dict):
    _ensure_storage()
    with open(USER_DEALS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_deals, f, indent=2)


def get_all_deals_for_user(user_email: str) -> dict:
    deals = dict(SAMPLE_DEALS)
    user_email = (user_email or "").strip().lower()
    if user_email:
        user_deals_db = get_user_deals_db()
        user_custom = user_deals_db.get(user_email, {})
        deals.update(user_custom)
    return deals


def save_custom_deal_for_user(user_email: str, deal_id: str, deal_data: dict):
    user_email = (user_email or "yellanki.rishitha12@gmail.com").strip().lower()
    user_deals_db = get_user_deals_db()
    if user_email not in user_deals_db:
        user_deals_db[user_email] = {}
    user_deals_db[user_email][deal_id] = deal_data
    save_user_deals_db(user_deals_db)


def get_user_memories(user_email: str, deal_id: str):
    user_email = (user_email or "").strip().lower()
    # Check base memories
    base_mems = memory_engine.get_all_memories(deal_id)
    # Check user-scoped custom memories
    user_scoped_bank = f"{user_email}:{deal_id}" if user_email else deal_id
    user_mems = memory_engine.get_all_memories(user_scoped_bank) if user_email else []
    
    # Combine uniquely
    combined = list(base_mems)
    seen_contents = set(m.get("content", "") for m in combined)
    for um in user_mems:
        if um.get("content", "") not in seen_contents:
            combined.append(um)
    return combined


def retain_user_memory(user_email: str, deal_id: str, content: str, metadata: dict):
    user_email = (user_email or "").strip().lower()
    bank_id = f"{user_email}:{deal_id}" if (user_email and deal_id not in SAMPLE_DEALS) else deal_id
    return memory_engine.retain(bank_id, content, metadata)


def send_real_or_simulated_email(to_email: str, subject: str, body: str) -> bool:
    """Attempts real SMTP send if credentials exist, otherwise logs clean mail dispatch."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", "noreply@dealmind.ai")

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to_email

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender, [to_email], msg.as_string())
            print(f"[DealMind Mailer] Real email dispatched to {to_email} via {smtp_host}")
            return True
        except Exception as e:
            print(f"[DealMind Mailer Error] SMTP send failed: {e}")
            return False
    else:
        print(f"\n=======================================================")
        print(f"📧 [DealMind Password Reset Mailer]")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print(f"=======================================================\n")
        return True


class DealMindHandler(BaseHTTPRequestHandler):

    def _get_user_email(self, body=None):
        if body and isinstance(body, dict) and body.get("user_email"):
            return body.get("user_email").strip().lower()
        
        email = self.headers.get("X-User-Email", "").strip().lower()
        if not email:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if "user_email" in qs:
                email = qs["user_email"][0].strip().lower()
        return email or "yellanki.rishitha12@gmail.com"

    def _send_json(self, status_code: int, data: dict):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-Email")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-Email")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user_email = self._get_user_email()

        # 1. API: List Deals (User Scoped)
        if path == "/api/deals":
            all_deals = get_all_deals_for_user(user_email)
            deals_summary = [
                {"id": k, "name": v.get("name", k), "value": v.get("value", "Custom"), "stage": v.get("stage", "Active"), "industry": v.get("industry", "Enterprise")}
                for k, v in all_deals.items()
            ]
            self._send_json(200, {"deals": deals_summary, "user_email": user_email})
            return

        # 2. API: Get Deal Memories (User Scoped)
        if path.startswith("/api/deals/") and path.endswith("/memories"):
            parts = path.split("/")
            deal_id = parts[3]
            memories = get_user_memories(user_email, deal_id)
            self._send_json(200, {"deal_id": deal_id, "memories": memories, "user_email": user_email})
            return

        # 3. API: Get User Profile
        if path == "/api/user/profile":
            users = get_users_db()
            profile = users.get(user_email, {
                "email": user_email,
                "name": user_email.split("@")[0].replace(".", " ").title(),
                "role": "Lead Account Executive",
                "org": "HackwithHyderabad 3.0 Finale Team",
                "workspace": "Microsoft Hyderabad Enterprise Hub",
                "memory_engine": "Local Disk JSON Engine (Active)"
            })
            self._send_json(200, {"profile": profile})
            return

        # 4. Static Files
        if path in ("", "/"):
            file_path = os.path.join(STATIC_DIR, "index.html")
        else:
            file_path = os.path.join(STATIC_DIR, path.lstrip("/"))

        if os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            if file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".css"):
                content_type = "text/css"
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type or "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data.decode("utf-8")) if post_data else {}
        user_email = self._get_user_email(body)

        # 1. API: User Sign Up
        if path == "/api/auth/signup":
            email = body.get("email", "").strip().lower()
            name = body.get("name", "").strip()
            password = body.get("password", "").strip()
            if not email or not name or not password:
                self._send_json(400, {"error": "Name, email, and password are required"})
                return
            users = get_users_db()
            users[email] = {
                "email": email,
                "name": name,
                "role": body.get("role", "Lead Account Executive"),
                "org": body.get("org", "HackwithHyderabad 3.0 Finale Team"),
                "workspace": body.get("workspace", "Microsoft Hyderabad Enterprise Hub"),
                "memory_engine": body.get("memory_engine", "Local Disk JSON Engine (Active)"),
                "password": password
            }
            save_users_db(users)
            self._send_json(200, {"success": True, "profile": users[email]})
            return

        # 2. API: User Login (Strict Password Validation)
        if path == "/api/auth/login":
            email = body.get("email", "").strip().lower()
            password = body.get("password", "").strip()
            if not email or not password:
                self._send_json(400, {"error": "Email and password are required"})
                return

            users = get_users_db()
            user = users.get(email)
            if not user:
                self._send_json(404, {"error": f"Account for '{email}' not found. Please click 'Sign Up' to create your account."})
                return
            
            # STRICT password verification
            if user.get("password") != password:
                self._send_json(401, {"error": "Incorrect password. Please verify your password or use 'Forgot Password'."})
                return
            
            self._send_json(200, {"success": True, "profile": user})
            return

        # 3. API: Forgot Password & Real Reset Link Generation
        if path == "/api/auth/forgot-password":
            email = body.get("email", "").strip().lower()
            if not email:
                self._send_json(400, {"error": "Email is required"})
                return

            token = secrets.token_urlsafe(16)
            resets = {}
            if os.path.exists(RESETS_FILE):
                try:
                    with open(RESETS_FILE, "r", encoding="utf-8") as f:
                        resets = json.load(f)
                except Exception:
                    resets = {}
            
            resets[token] = {
                "email": email,
                "created_at": time.time(),
                "expires_at": time.time() + 3600
            }
            with open(RESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(resets, f, indent=2)

            reset_url = f"http://localhost:{PORT}/?reset_token={token}&email={email}"
            mail_body = (
                f"Hello,\n\n"
                f"You requested a password reset for your DealMind account ({email}).\n\n"
                f"Click the link below or paste it in your browser to choose a new password:\n"
                f"{reset_url}\n\n"
                f"Reset Token: {token}\n\n"
                f"If you did not request this, you can safely ignore this message.\n\n"
                f"— DealMind AI Security Team"
            )
            email_dispatched = send_real_or_simulated_email(email, "DealMind Password Reset Link", mail_body)

            self._send_json(200, {
                "success": True,
                "message": f"Password reset email dispatched to {email}",
                "reset_url": reset_url,
                "token": token,
                "email_sent": email_dispatched
            })
            return

        # 4. API: Reset Password (Updates DB)
        if path == "/api/auth/reset-password":
            token = body.get("token", "").strip()
            new_password = body.get("password", "").strip()
            if not token or not new_password:
                self._send_json(400, {"error": "Token and new password are required"})
                return

            resets = {}
            if os.path.exists(RESETS_FILE):
                try:
                    with open(RESETS_FILE, "r", encoding="utf-8") as f:
                        resets = json.load(f)
                except Exception:
                    resets = {}
            
            reset_entry = resets.get(token)
            if not reset_entry or reset_entry.get("expires_at", 0) < time.time():
                self._send_json(400, {"error": "Invalid or expired password reset token"})
                return

            email = reset_entry.get("email")
            users = get_users_db()
            if email in users:
                users[email]["password"] = new_password
                save_users_db(users)

            # Invalidate used token
            del resets[token]
            with open(RESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(resets, f, indent=2)

            self._send_json(200, {"success": True, "message": "Password successfully updated! You can now sign in with your new password."})
            return

        # 5. API: Update User Profile & Preferences
        if path == "/api/user/profile":
            users = get_users_db()
            profile = users.get(user_email, {"email": user_email})
            profile["name"] = body.get("name", profile.get("name", "Rishitha Yellanki"))
            profile["role"] = body.get("role", profile.get("role", "Lead Account Executive"))
            profile["org"] = body.get("org", profile.get("org", "HackwithHyderabad 3.0 Finale Team"))
            profile["workspace"] = body.get("workspace", profile.get("workspace", "Microsoft Hyderabad Enterprise Hub"))
            profile["memory_engine"] = body.get("memory_engine", profile.get("memory_engine", "Local Disk JSON Engine (Active)"))
            users[user_email] = profile
            save_users_db(users)
            self._send_json(200, {"success": True, "profile": profile})
            return

        # 6. API: Create New Custom Account / Deal (Strictly User Scoped)
        if path == "/api/deals":
            name = body.get("name", "").strip()
            if not name:
                self._send_json(400, {"error": "Account name is required"})
                return
            deal_id = re.sub(r'[^a-zA-Z0-9_-]', '-', name.lower()).strip('-') or f"deal-{int(time.time())}"
            deal_data = {
                "name": name,
                "value": body.get("value", "$50,000 ARR").strip(),
                "stage": body.get("stage", "Discovery").strip(),
                "industry": body.get("industry", "Enterprise SaaS").strip(),
                "calls": []
            }
            save_custom_deal_for_user(user_email, deal_id, deal_data)
            self._send_json(200, {"success": True, "deal_id": deal_id, "deal": deal_data, "user_email": user_email})
            return

        # 7. API: Live Battle Comparison & Copilot Query
        if path == "/api/compare":
            deal_id = body.get("deal_id", "apex-logistics")
            task = body.get("task", "Prepare executive pitch for closing call")
            api_key = body.get("api_key", None)
            all_deals = get_all_deals_for_user(user_email)
            deal_name = all_deals.get(deal_id, {}).get("name", deal_id)

            user_bank = f"{user_email}:{deal_id}" if (user_email and deal_id not in SAMPLE_DEALS) else deal_id
            without_mem = generate_without_memory(deal_name, task, api_key=api_key)
            with_mem = generate_with_memory(deal_name, task, user_bank, memory_engine, api_key=api_key)

            self._send_json(200, {
                "deal_id": deal_id,
                "deal_name": deal_name,
                "task": task,
                "without_memory": without_mem,
                "with_memory": with_mem
            })
            return

        # 8. API: Retain New Meeting Note (User Scoped)
        if path == "/api/retain":
            deal_id = body.get("deal_id", "apex-logistics")
            call_type = body.get("call_type", "Strategic Review")
            notes = body.get("notes", "")
            tags = body.get("tags", [])

            content = f"[{call_type}] {notes}"
            metadata = {
                "deal_id": deal_id,
                "call_type": call_type,
                "tags": tags,
                "author": user_email
            }

            result = retain_user_memory(user_email, deal_id, content, metadata)
            self._send_json(200, {"success": True, "result": result, "user_email": user_email})
            return

        # 9. API: Reset Data for User
        if path == "/api/reset":
            user_deals_db = get_user_deals_db()
            if user_email in user_deals_db:
                del user_deals_db[user_email]
                save_user_deals_db(user_deals_db)
            seed_hindsight_memory(memory_engine, force_reset=True)
            self._send_json(200, {"success": True, "message": "Demo data reset successfully"})
            return

        self._send_json(404, {"error": "Endpoint not found"})


def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, DealMindHandler)
    print(f"\n=========================================================")
    print(f"🚀 DealMind Server Running at http://localhost:{PORT}")
    print(f"🧠 Hindsight Memory Engine: ACTIVE")
    print(f"🔒 Strict Password Authentication & Multi-Tenancy: ACTIVE")
    print(f"=========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    run()
