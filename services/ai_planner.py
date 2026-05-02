import os
import json
from anthropic import Anthropic
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def analyze_training_patterns(activities: list) -> dict:
    """
    Analyze Strava history to find preferred training days
    and recent fitness level.
    """
    if not activities:
        return {}

    # Count activities by day of week
    day_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0}
    day_names = {0:"Monday", 1:"Tuesday", 2:"Wednesday", 
                 3:"Thursday", 4:"Friday", 5:"Saturday", 6:"Sunday"}

    recent_miles = []
    recent_vert = []
    long_runs = []

    run_types = ["Run", "TrailRun"]
    hike_types = ["Hike"]

    for a in activities:
        if a.get("date"):
            try:
                date = datetime.fromisoformat(str(a["date"]).replace("Z", ""))
                day_counts[date.weekday()] += 1
            except:
                pass

        # Track recent fitness
        dist = a.get("distance_miles") or 0
        vert = a.get("elevation_gain_ft") or 0
        atype = a.get("activity_type") or ""

        if atype in run_types:
            recent_miles.append(dist)
            recent_vert.append(vert)
            if dist >= 10:
                long_runs.append(dist)

    # Find top 4 training days
    sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
    preferred_days = [day_names[d[0]] for d in sorted_days[:4] if d[1] > 0]

    return {
        "preferred_days": preferred_days[:4],
        "avg_run_miles": round(sum(recent_miles) / len(recent_miles), 1) if recent_miles else 0,
        "avg_run_vert": round(sum(recent_vert) / len(recent_vert), 0) if recent_vert else 0,
        "longest_recent_run": round(max(long_runs), 1) if long_runs else 0,
        "total_recent_activities": len(activities)
    }


def generate_weekly_plan(
    goal: dict,
    recent_activities: list,
    week_start: datetime
) -> dict:
    """
    Call Claude API to generate a weekly training plan.
    Returns a structured plan with 4 workout slots.
    """
    patterns = analyze_training_patterns(recent_activities)

    week_end = week_start + timedelta(days=6)
    days_of_week = ["Monday", "Tuesday", "Wednesday", 
                    "Thursday", "Friday", "Saturday", "Sunday"]

    # Build recent activity summary for context
    recent_summary = []
    for a in recent_activities[:10]:
        recent_summary.append(
            f"- {a.get('name')} | {a.get('activity_type')} | "
            f"{a.get('distance_miles')}mi | {a.get('elevation_gain_ft')}ft | "
            f"{a.get('date', '')[:10]}"
        )

    targets = goal.get("training_targets", {})

    prompt = f"""You are an expert ultramarathon coach. Generate a weekly training plan for an athlete.

ATHLETE CONTEXT:
- Goal Race: {goal.get('race_name')}
- Race Date: {goal.get('race_date', '')[:10]}
- Race Distance: {goal.get('race_distance_miles')} miles
- Race Elevation Gain: {goal.get('race_elevation_gain_ft')} ft
- Weeks to Race: {goal.get('weeks_to_race')}
- Current Training Phase: {goal.get('current_phase')}
- Location: Salt Lake City, Utah (Wasatch Mountains)

WEEKLY TARGETS:
- Weekly Miles: {targets.get('target_weekly_miles')} miles
- Weekly Vert: {targets.get('target_weekly_vert_ft')} ft
- Long Run: {targets.get('long_run_range_miles')} miles / {targets.get('long_run_vert_range_ft')} ft gain
- Vert Day: {targets.get('vert_day_range_ft')} ft gain

ATHLETE TRAINING PATTERNS:
- Preferred training days (from history): {', '.join(patterns.get('preferred_days', []))}
- Average run distance: {patterns.get('avg_run_miles')} miles
- Longest recent run: {patterns.get('longest_recent_run')} miles

RECENT ACTIVITIES (last 10):
{chr(10).join(recent_summary)}

WEEK TO PLAN: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}

INSTRUCTIONS:
1. Place exactly 4 workouts across the 7 days (Monday-Sunday)
2. Use the athlete's preferred training days from their history
3. Never place two hard workouts back to back (long run and vert day need a rest day between them)
4. The 4 workout types are: easy_run, long_run, vert_day, track_workout
5. For long_run and vert_day suggest a specific real trail in the Wasatch Mountains near Salt Lake City
6. Consider what the athlete did recently - don't repeat the same trails

Respond ONLY with a valid JSON object, no other text, in this exact format:
{{
  "week_notes": "Brief coaching note about this week's focus (1-2 sentences)",
  "workouts": [
    {{
      "day": "Monday",
      "type": "easy_run",
      "label": "Easy Run",
      "target_miles": 5.0,
      "target_vert_ft": 200,
      "target_time_hours": 0.75,
      "suggested_trail": null,
      "trail_description": null,
      "notes": "Keep effort conversational, focus on recovery"
    }},
    {{
      "day": "Wednesday", 
      "type": "track_workout",
      "label": "Track Workout",
      "target_miles": 6.0,
      "target_vert_ft": 100,
      "target_time_hours": 1.0,
      "suggested_trail": null,
      "trail_description": null,
      "notes": "6x800m at 5k effort with 90 sec recovery"
    }},
    {{
      "day": "Saturday",
      "type": "long_run",
      "label": "Long Trail Run",
      "target_miles": 18.0,
      "target_vert_ft": 2800,
      "target_time_hours": 4.0,
      "suggested_trail": "Wasatch Crest Trail",
      "trail_description": "18mi loop with steady climbing, technical singletrack",
      "notes": "Keep effort easy, focus on time on feet"
    }},
    {{
      "day": "Sunday",
      "type": "vert_day",
      "label": "Vert Day",
      "target_miles": 8.0,
      "target_vert_ft": 4500,
      "target_time_hours": 3.5,
      "suggested_trail": "Mount Olympus",
      "trail_description": "Steep sustained climb, 4,100ft gain in 4.2 miles",
      "notes": "Power hike the climbs, run the descents"
    }}
  ]
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Clean up any markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        plan = json.loads(response_text)
        return {"success": True, "plan": plan}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Could not parse AI response: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}