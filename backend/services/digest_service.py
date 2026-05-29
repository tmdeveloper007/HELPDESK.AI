import os
import resend
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

# Try importing supabase from main if available, else initialize here
try:
    from backend.main import supabase, gemini_service
except ImportError:
    supabase = None
    gemini_service = None

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

resend.api_key = os.environ.get("RESEND_API_KEY", "")

def get_weekly_stats() -> dict:
    if not supabase:
        print("[DigestService] Supabase not initialized.")
        return {}

    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    
    try:
        # Get last 7 days tickets
        response = supabase.table("tickets").select("*").gte("created_at", seven_days_ago).execute()
        tickets = response.data or []
        
        # Get previous 7 days tickets for comparison
        fourteen_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()
        prev_response = supabase.table("tickets").select("*").gte("created_at", fourteen_days_ago).lt("created_at", seven_days_ago).execute()
        prev_tickets = prev_response.data or []
        
        total_tickets = len(tickets)
        prev_total = len(prev_tickets)
        
        # Calculate percentage change
        if prev_total > 0:
            percent_change = ((total_tickets - prev_total) / prev_total) * 100
        else:
            percent_change = 100.0 if total_tickets > 0 else 0.0
            
        resolved_tickets = [t for t in tickets if t.get("status", "").lower() == "resolved"]
        resolved_count = len(resolved_tickets)
        
        resolution_rate = (resolved_count / total_tickets * 100) if total_tickets > 0 else 0
        
        # SLA breach count - check if sla_breach_at exists and is in the past, or if metadata indicates breach
        sla_breach_count = 0
        for t in tickets:
            if t.get("sla_breach_at"):
                # simplified check
                sla_breach_count += 1
                
        # Top 3 categories
        categories = {}
        for t in tickets:
            cat = t.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
            
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "total_tickets": total_tickets,
            "prev_total": prev_total,
            "percent_change": round(percent_change, 1),
            "resolved_count": resolved_count,
            "resolution_rate": round(resolution_rate, 1),
            "sla_breach_count": sla_breach_count,
            "top_categories": top_categories
        }
    except Exception as e:
        print(f"[DigestService] Error getting stats: {e}")
        return {}

def generate_ai_summary(stats: dict) -> str:
    if not gemini_service or not gemini_service._initialized:
        return "AI Summary is currently unavailable."
        
    try:
        prompt = (
            f"You are an IT manager assistant. Summarize this week's helpdesk performance in 3 sentences: {stats}. "
            "Make it professional and highlight any key trends or concerns."
        )
        response = gemini_service.client.models.generate_content(
            model=gemini_service.model_name,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[DigestService] AI Summary Error: {e}")
        return "Failed to generate AI summary."

def send_digest_email(admin_email: str, stats: dict, summary: str):
    if not resend.api_key:
        print("[DigestService] RESEND_API_KEY missing. Skipping email.")
        return
        
    top_categories_html = "".join([f"<li>{c[0]}: {c[1]} tickets</li>" for c in stats.get("top_categories", [])])
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px; border-radius: 8px;">
            <h2 style="color: #10b981;">Weekly Helpdesk Digest</h2>
            
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #334155;">AI Summary</h3>
                <p style="font-style: italic;">{summary}</p>
            </div>
            
            <h3>Weekly Statistics</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px 0;"><strong>Total Tickets</strong></td>
                    <td style="padding: 8px 0; text-align: right;">{stats.get('total_tickets', 0)} ({stats.get('percent_change', 0):+}% from last week)</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px 0;"><strong>Resolution Rate</strong></td>
                    <td style="padding: 8px 0; text-align: right;">{stats.get('resolution_rate', 0)}%</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px 0;"><strong>SLA Breaches</strong></td>
                    <td style="padding: 8px 0; text-align: right; color: {'#ef4444' if stats.get('sla_breach_count', 0) > 0 else '#333'};">{stats.get('sla_breach_count', 0)}</td>
                </tr>
            </table>
            
            <h3>Top Ticket Categories</h3>
            <ul>
                {top_categories_html}
            </ul>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://helpdeskaiv1.vercel.app/" style="background-color: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">View Full Dashboard</a>
            </div>
        </div>
      </body>
    </html>
    """
    
    try:
        r = resend.Emails.send({
            "from": "Helpdesk.AI <onboarding@resend.dev>",
            "to": admin_email,
            "subject": "Your Weekly Helpdesk AI Digest",
            "html": html_content
        })
        print(f"[DigestService] Email sent to {admin_email}: {r}")
        return r
    except Exception as e:
        print(f"[DigestService] Error sending email: {e}")
        return None
