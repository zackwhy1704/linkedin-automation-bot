"""
Centralized Prompt Templates for AI Service
All prompts for content generation, analysis, and personalization
"""

# Shared base for all post formats
_POST_BASE = """You are a LinkedIn ghostwriter for a tech professional. Write in a personal, storytelling style that feels authentic and human.

User Profile:
- Industry: {industry}
- Skills: {skills}
- Career Goals: {career_goals}
- Tone: {tone}

Create a LinkedIn post about: {theme}

"""

_POST_RULES = """
CRITICAL SPACING RULES:
- Put a BLANK LINE between EVERY section/beat above
- Put a BLANK LINE between EVERY single thought/sentence
- ONE sentence per line maximum
- Checklist items (☑️/✅) can be grouped together without blank lines between them
- Everything else gets breathing room — white space is your friend
- LinkedIn rewards posts that are easy to scan — make it airy, not dense
- NEVER put two regular sentences back-to-back without a blank line

Requirements:
- Length: 250-400 words (longer, more story-telling format with depth)
- Include 3-5 relevant hashtags at the very end (after a blank line)
- DO NOT use generic LinkedIn-speak ("excited to share", "thrilled to announce", "I'm humbled")
- Sound like a builder sharing from the trenches, not a marketer
- Make it feel like a real story someone would actually want to read
- DO NOT pad or bloat the post — every line should earn its place
- Use ☑️ and ✅ emojis for lists, never plain bullet points or dashes
- Include engaging questions to encourage audience interaction and comments

Return ONLY the post content with hashtags. No commentary, no intro, no explanation."""

# FORMAT A: Story Arc (Hook → Declaration → Checklist → Details → Contrarian → Reframe → Question)
_FORMAT_A = """STRUCTURE TO FOLLOW:

1. HOOK (1-2 short punchy sentences — grab attention)
2. DECLARATION (1 short sentence — what you're building/doing)
3. SETUP + CHECKLIST ("The concept is simple:" then 2-4 items using ☑️)
4. NARRATIVE MOMENT (1 vivid, personal observation)
5. DETAIL SECTION (3-4 lines using ✅ showing a process step by step)
6. CONTRARIAN INSIGHT (2 short lines — "This isn't X." / "It's Y.")
7. REFRAME ("We often think X. But I'm finding Y.")
8. PERSONAL REACTION (1 short sentence — how you feel)
9. BIGGER PICTURE (1 sentence — future or industry impact)
10. ENGAGEMENT QUESTION (1 specific question to invite comments)

REFERENCE EXAMPLE:
---
I've spent the last 6 weeks staring at a terminal, watching an AI "think" in real-time.

I'm building what I call Skill Files.

The concept is simple:
☑️ Take a complex business workflow.
Convert it into a plain text Markdown (.md) file.
☑️ Give it to an AI Agent with strict guardrails.

Then, I sit back and watch the logs scroll.

It's fascinating to read the reasoning process as it executes:

✅ It analyzes the request against my .md instructions.
✅ It realizes a step is ambiguous.
✅ It consults the "Strict Guidelines" section I wrote.
✅ It self-corrects before executing the action.

This isn't black-box magic.
It's transparent logic.

We often think automation requires heavy engineering.

But I'm finding that clear, structured English is the most powerful programming language we have right now.

I'm pretty impressed.

The future of work isn't just about the output, it's about trusting the reasoning behind it.

Has anyone else tried strictly text-based agent orchestration?
---"""

# FORMAT B: Lesson Learned (Problem → What I tried → What worked → Takeaway)
_FORMAT_B = """STRUCTURE TO FOLLOW:

1. HOOK (Start with a mistake, failure, or surprising result — be vulnerable)
2. CONTEXT (1-2 sentences — what you were trying to do)
3. WHAT I TRIED (2-3 items using ☑️ — the approaches that didn't work or what you tested)
4. TURNING POINT (1 sentence — the moment things clicked)
5. WHAT ACTUALLY WORKED (2-3 items using ✅ — the solution or insight)
6. KEY TAKEAWAY (1-2 bold sentences — the lesson distilled)
7. ENGAGEMENT QUESTION (ask others about their experience with the same problem)

REFERENCE EXAMPLE:
---
I wasted 3 days trying to make my AI agent reliable.

Turns out the problem wasn't the AI.

It was my instructions.

Here's what I tried first:
☑️ More detailed prompts.
☑️ Fine-tuning parameters.
☑️ Adding retry logic everywhere.

Nothing worked consistently.

Then I did something different.

I stopped writing prompts and started writing documentation.

✅ Clear step-by-step workflows in plain Markdown.
✅ Explicit edge cases and how to handle them.
✅ A "when in doubt" section with fallback rules.

The results were night and day.

The lesson?

AI doesn't need better prompts.

It needs better onboarding — just like a new team member.

What's the most counterintuitive thing you've learned building with AI?
---"""

# FORMAT C: Hot Take / Contrarian (Bold claim → Evidence → Flip the script)
_FORMAT_C = """STRUCTURE TO FOLLOW:

1. BOLD OPENING (1 provocative statement that challenges conventional wisdom)
2. ACKNOWLEDGMENT (1-2 sentences — "I know this sounds [crazy/wrong/backwards]...")
3. THE COMMON BELIEF (What most people think, framed fairly)
4. YOUR EVIDENCE (3-4 lines using ✅ — what you've seen/built/experienced that says otherwise)
5. THE FLIP (2 short punchy lines — restate your contrarian view with conviction)
6. NUANCE (1-2 sentences — show you're not just being edgy, there's real depth here)
7. FORWARD-LOOKING STATEMENT (1 sentence — where this is heading)
8. ENGAGEMENT QUESTION (challenge others to share their take)

REFERENCE EXAMPLE:
---
Unpopular opinion: most "AI-powered" products are just fancy templates.

I know that sounds harsh.

The industry loves to slap "AI" on everything right now.

But here's what I'm actually seeing when I look under the hood:

✅ Hard-coded responses dressed up as "intelligence."
✅ Simple if/else logic with a ChatGPT wrapper.
✅ Zero reasoning, zero adaptation, zero learning.

That's not AI.

That's a mail merge with extra steps.

Real AI-powered means the system can reason through ambiguity without you holding its hand.

I've been building agents that actually do this — and the difference is obvious once you see it.

The bar is about to go way up.

What's the most overhyped "AI feature" you've seen recently?
---"""

# FORMAT D: Behind the Scenes / Build Log (Show the work)
_FORMAT_D = """STRUCTURE TO FOLLOW:

1. HOOK (What you're building — frame it as a journey, not an announcement)
2. THE WHY (1-2 sentences — why this matters to you personally)
3. WHAT I DID THIS WEEK (3-5 items using ✅ — specific, tangible progress)
4. HONEST MOMENT (1-2 sentences — what's hard, what surprised you, what broke)
5. WHAT I LEARNED (1-2 punchy sentences — the insight from doing the work)
6. WHAT'S NEXT (1 sentence — where you're heading)
7. ENGAGEMENT QUESTION (invite others who are building similar things)

REFERENCE EXAMPLE:
---
I've been building an AI agent framework for the last 2 weeks.

Not because someone asked me to.

Because I got tired of watching automation tools do the same dumb thing over and over.

Here's what I shipped this week:

✅ A reasoning engine that reads plain English workflows.
✅ Guardrails that prevent the agent from going off-script.
✅ A logging system so I can watch every decision it makes.
✅ Session recovery when things inevitably crash.

The hardest part?

Getting the agent to know when it doesn't know something.

That's the real unlock — teaching AI to pause instead of guess.

Next up: making it learn from its own mistakes.

Anyone else deep in the agent-building rabbit hole right now?
---"""

# FORMAT E: Before/After Transformation (Contrast old vs new)
_FORMAT_E = """STRUCTURE TO FOLLOW:

1. HOOK (State the transformation — "I used to X. Now I Y.")
2. THE BEFORE (2-3 items using ☑️ — how things used to be, paint the pain)
3. WHAT CHANGED (1-2 sentences — the catalyst or discovery)
4. THE AFTER (2-3 items using ✅ — how things are now, show the contrast)
5. THE REAL DIFFERENCE (1-2 punchy sentences — what actually shifted, not just tools but mindset)
6. PERSONAL REFLECTION (1 sentence — how this changed your thinking)
7. ENGAGEMENT QUESTION (ask about others' transformation moments)

REFERENCE EXAMPLE:
---
6 months ago I was writing automation scripts the "normal" way.

☑️ Hundreds of lines of Python for every workflow.
☑️ Brittle logic that broke if anything changed.
☑️ Hours debugging edge cases I didn't anticipate.

Then I tried something radically different.

I wrote the entire workflow in plain English.

Gave it to an AI agent.

And watched it handle the edge cases on its own.

✅ 90% less code to maintain.
✅ The agent adapts when inputs change.
✅ I spend time thinking instead of debugging.

The difference isn't just efficiency.

It's a completely different relationship with the work.

I went from writing instructions for a machine to writing instructions for a thinker.

That shift changes everything.

What's a workflow you'd love to hand off to an AI agent?
---"""

import random as _random

# All format templates with names for logging
POST_FORMATS = {
    'A - Story Arc': _FORMAT_A,
    'B - Lesson Learned': _FORMAT_B,
    'C - Hot Take': _FORMAT_C,
    'D - Build Log': _FORMAT_D,
    'E - Before/After': _FORMAT_E,
}

def get_post_generation_prompt(**kwargs):
    """Get a randomly selected post generation prompt format"""
    format_name = _random.choice(list(POST_FORMATS.keys()))
    selected_format = POST_FORMATS[format_name]
    print(f"  [Format Selected: {format_name}]")
    return _POST_BASE.format(**kwargs) + selected_format + _POST_RULES

# Keep backward compatibility — uses Format A as default
POST_GENERATION_PROMPT = _POST_BASE + _FORMAT_A + _POST_RULES

# Relevance Scoring Prompt
RELEVANCE_SCORING_PROMPT = """Analyze if this LinkedIn post is relevant for a professional with the following profile:

User Profile:
- Industry: {industry}
- Skills: {skills}
- Career Goals: {career_goals}
- Interests: {interests}

Post Content:
{post_content}

Post Author:
- Name: {author_name}
- Title: {author_title}

Score the relevance on a scale of 0.0 to 1.0 where:
- 1.0 = Highly relevant (directly related to user's industry, skills, or career goals)
- 0.7-0.9 = Very relevant (related field or valuable insights)
- 0.5-0.6 = Moderately relevant (tangentially related)
- 0.0-0.4 = Not relevant (unrelated content)

Consider:
1. Does the post relate to the user's industry or skills?
2. Is the author a potential valuable connection (recruiter, hiring manager, industry peer)?
3. Does the content provide value for career growth?
4. Is this content the user would naturally engage with?

Return ONLY a number between 0.0 and 1.0, nothing else."""

# Comment Generation Prompt — uses random style for variety
_COMMENT_STYLES = [
    "SHARE A SHORT PERSONAL EXPERIENCE that relates to what the author said. Start with something like 'I ran into this exact thing when...' or 'This happened to me too —'. Keep it real and specific.",
    "ASK A GENUINE FOLLOW-UP QUESTION about one specific point in the post. Show curiosity. Don't be generic — reference something concrete they said.",
    "ADD A NEW ANGLE or insight the author didn't mention. Build on their point with your own take. Start with something like 'One thing I'd add...' or 'This also connects to...'.",
    "RESPECTFULLY CHALLENGE or push back on one small point, then agree with the bigger idea. Show you're thinking critically, not just nodding along.",
    "GIVE A SPECIFIC COMPLIMENT about one exact thing they said (not 'great post'). Quote or reference a specific line, then explain why it resonated.",
    "SHARE A QUICK TIP or resource related to the topic. Something like 'If you haven't tried X for this, it's a game changer' or 'I found that Y helps a lot with this'.",
]

COMMENT_GENERATION_PROMPT = """Generate a comment for this LinkedIn post.

Post Content:
{post_content}

Post Author:
- Name: {author_name}
- Title: {author_title}

Your Profile (commenter):
- Industry: {industry}
- Skills: {skills}
- Tone: {tone}

COMMENT STYLE TO USE:
{comment_style}

RULES:
- Length: 15-40 words (short and punchy, NOT an essay)
- Sound like a real human, not a bot
- Be specific to THIS post — reference something concrete from the content
- NEVER start with "Great post", "Love this", "Thanks for sharing", "This resonates", or "Well said"
- NEVER use phrases like "couldn't agree more" or "this is so important"
- Write like you're replying to a friend's post, not writing a formal letter
- Vary your sentence structure — don't always start with "I"
- DO NOT use emojis unless it feels natural (max 1)

{recent_comments_instruction}

Return ONLY the comment text. No quotes, no formatting, no explanation."""

def get_comment_style():
    """Return a random comment style for variety"""
    return _random.choice(_COMMENT_STYLES)

# Profile Analysis Prompt
PROFILE_ANALYSIS_PROMPT = """Analyze this LinkedIn profile and determine if this person is relevant for job-seeking networking.

Profile Information:
Name: {name}
Title: {title}
Company: {company}
About/Bio: {bio}
Additional Context: {context}

User's Job Search:
- Target Roles: {target_roles}
- Target Industries: {target_industries}
- Current Industry: {user_industry}

Analysis Tasks:
1. Is this person a recruiter? (Look for keywords: recruiter, talent acquisition, hiring, staffing, HR)
2. Is this person a hiring manager or decision maker? (Look for: director, manager, VP, CTO, head of, lead)
3. Is this person in a relevant industry?
4. Connection value score (0.0-1.0) for networking

Return your analysis in this exact format:
is_recruiter: [yes/no]
is_hiring_manager: [yes/no]
is_relevant: [yes/no]
connection_value: [0.0-1.0]
reasoning: [one sentence explanation]"""

# Personalized Message Generation Prompt
MESSAGE_GENERATION_PROMPT = """Generate a personalized LinkedIn connection request message.

Recipient Profile:
- Name: {recipient_name}
- Title: {recipient_title}
- Company: {recipient_company}
- Context: {context}

Sender Profile:
- Industry: {sender_industry}
- Skills: {sender_skills}
- Career Goals: {sender_goals}

Message Purpose: {purpose}

Requirements:
- Length: 200-300 characters (LinkedIn connection message limit)
- Personalized (mention their role, company, or recent activity)
- Explain why you want to connect
- Professional and genuine
- Include a subtle call-to-action
- Don't be overly salesy or desperate

Return only the message text, no additional formatting."""

# Hashtag Optimization Prompt
HASHTAG_OPTIMIZATION_PROMPT = """Suggest 3-5 relevant and effective LinkedIn hashtags for this post.

Post Content:
{post_content}

User Industry: {industry}
Target Audience: {target_audience}

Requirements:
- Mix of popular and niche hashtags
- Relevant to content and industry
- Help with discoverability
- Not overly generic (#business, #motivation)
- Include some job-seeking hashtags if relevant

Return only the hashtags separated by spaces, like: #hashtag1 #hashtag2 #hashtag3"""

# Auto-Reply Generation Prompt
AUTO_REPLY_PROMPT = """Generate a thoughtful reply to this comment on your LinkedIn post.

Original Post:
{original_post}

Comment:
{comment_text}

Commenter: {commenter_name}

Your Profile:
- Industry: {industry}
- Tone: {tone}

Requirements:
- Length: 20-40 words
- Acknowledge their comment
- Add value or continue the conversation
- Professional and friendly
- Natural and human-like
- If it's a question, answer helpfully
- If it's praise, thank them gracefully

Return only the reply text."""

# Improved Template Comments (Fallback)
IMPROVED_TEMPLATE_COMMENTS = [
    "This is a really interesting perspective on {topic}. Thanks for sharing your insights!",
    "I've experienced something similar with {topic}. Your approach makes a lot of sense.",
    "Great breakdown of {topic}. This is particularly relevant in today's {industry}.",
    "Appreciate you sharing this! The point about {topic} really resonates with me.",
    "This is valuable advice for anyone working with {topic}. Thanks for posting!",
    "I hadn't thought about {topic} from this angle before. Interesting take!",
    "Your experience with {topic} is really insightful. Would love to hear more about this.",
    "This aligns with what I've been seeing in {industry}. Thanks for articulating it so well!",
]

def get_prompt(prompt_name, **kwargs):
    """
    Get a prompt template and format it with provided arguments

    Args:
        prompt_name: Name of the prompt (e.g., 'post_generation', 'comment_generation')
        **kwargs: Arguments to format the prompt with

    Returns:
        Formatted prompt string
    """
    prompts = {
        'post_generation': POST_GENERATION_PROMPT,
        'relevance_scoring': RELEVANCE_SCORING_PROMPT,
        'comment_generation': COMMENT_GENERATION_PROMPT,
        'profile_analysis': PROFILE_ANALYSIS_PROMPT,
        'message_generation': MESSAGE_GENERATION_PROMPT,
        'hashtag_optimization': HASHTAG_OPTIMIZATION_PROMPT,
        'auto_reply': AUTO_REPLY_PROMPT,
    }

    prompt_template = prompts.get(prompt_name)
    if not prompt_template:
        raise ValueError(f"Unknown prompt name: {prompt_name}")

    try:
        return prompt_template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required argument for prompt '{prompt_name}': {e}")
