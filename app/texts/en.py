from app.custom_emojis import ce


TEXTS = {
    "welcome": (
        "Hi, {name}!\n\n"
        "{project_name} helps Telegram projects grow and lets users earn {currency_name} for simple actions. "
        "You can promote channels, groups, posts, bots, reactions and premium boost tasks.\n\n"
        f"├ {ce('earn')} Earn\n├ {ce('ads')} Advertise\n├ {ce('checks')} Checks\n├ {ce('profile')} Profile\n└ {ce('subscription_check')} Subscription check"
    ),
    "earn": f"{ce('earn')} Available earning categories:\n\n├ {ce('channel')} Channels: {{channel}}\n├ {ce('group')} Groups: {{group}}\n├ {ce('post')} Posts: {{post}}\n├ {ce('bot')} Bots: {{bot}}\n├ {ce('reactions')} Reactions: {{reaction}}\n└ {ce('boost')} Boost: {{boost}}",
    "profile": f"{ce('profile')} Profile\n\n{{display_name}}\n├ {ce('id')} ID: {{telegram_id}}\n├ {ce('balance')} Balance: {{balance}} {{currency_name}}\n├ {ce('levels')} Level: {{level_name}}\n├ {ce('xp')} XP: {{xp}}, next level in {{xp_left}}\n├ {ce('referrals')} Referrals: {{referrals_count}}\n└ {ce('notifications_on')} Notifications: {{notifications}}",
    "topup": f"{ce('payment')} Top up\n\nCurrent balance: {{balance}} {{currency_name}}\n\nChoose a package or enter a Telegram Stars amount.",
    "topup_confirm": f"{ce('payment')} Confirm purchase\n\n• Amount: {{amount}} {{currency_name}}\n• Price: {{stars}} {ce('stars')}\n\nThe balance will update after a successful Telegram Stars payment.",
    "topup_custom": "Enter Telegram Stars amount.",
    "topup_done": f"{ce('success')} Balance topped up: +{{amount}} {{currency_name}}.",
    "refs": f"{ce('referrals')} Referrals\n\nYour link:\n{{referral_link}}\n\n• Invited: {{referrals_count}}\n• Earned: {{referral_earned}} {{currency_name}}",
    "refs_stats": f"{ce('statistics')} Referral stats\n├ Regular: +{{regular}}\n├ Premium: +{{premium}}\n├ OP: +{{op}}\n├ Deposits: {{deposit_percent}}%\n└ Tasks: {{task_percent}}%",
    "levels": f"{ce('levels')} Levels\n\n• Current: {{level_name}}\n• XP: {{xp}}\n• Next in: {{xp_left}}\n\n{{levels_table}}",
    "xp_help": (
        "XP is earned from tasks, referrals and balance top-ups.\n\n"
        "For each completed task, XP matches the task reward: "
        "a 750 GRAM task gives 750 XP, a 1 400 GRAM task gives 1 400 XP."
    ),
    "notifications_on": "Notifications enabled.",
    "notifications_off": "Notifications disabled.",
    "advertise": f"{ce('ads')} Ad cabinet {{project_name}}\n\n{ce('balance')} Balance: {{balance}} {{currency_name}}\n\nChoose what to promote. I will show the price and ask for confirmation before launch.",
    "ad_channel_intro": (
        "Choose subscription type:\n\n"
        "1. All users — broad audience.\nMinimum price: 750 {currency_name}\n\n"
        "2. Telegram Premium only — higher quality audience.\nMinimum price: 1 400 {currency_name}"
    ),
    "ad_group_intro": (
        "Choose subscription type:\n\n"
        "1. All users — broad audience.\nMinimum price: 1 000 {currency_name}\n\n"
        "2. Telegram Premium only — higher quality audience.\nMinimum price: 1 500 {currency_name}"
    ),
    "ad_post_intro": "Post promotion. Choose views or reactions.",
    "ad_bot_intro": "Bot promotion. Choose simple start or extra conditions.",
    "ad_reaction_intro": (
        "Rules for reaction tasks:\n\n"
        "1. Do not create reaction tasks for Telegram Stars.\n\n"
        "2. Screenshots must be possible for the channel. If content saving is blocked, users will not be able to confirm completion.\n\n"
        "⚠️ Rule violations may lead to task removal or account limits.\n\n"
        "Now configure the task audience."
    ),
    "ad_boost_intro": "⚡ Choose boost period:\n\n📊 7 days — 21 000 {currency_name}\n📊 30 days — 90 000 {currency_name}",
    "ad_boost_amount": (
        "A 15% fee applies when paying with {currency_name}.\n"
        "You can donate from 50 Stars to disable the fee for 24 hours.\n\n"
        "One boost charge for {days} days: {price} {currency_name}\n"
        "Your balance: {balance} {currency_name}\n\n"
        "Enter the number of boost charges.\n\n"
        "Maximum for your balance: {max_amount}"
    ),
    "ad_manual_filters": "Describe audience filters in one message.",
    "ad_send_url": "Send the target link. You may add chat_id after it.",
    "ad_send_reward": "Enter the reward per completion in {currency_name}. Example: 750 or 1400{min_line}",
    "ad_bad_reward": "Enter a valid amount greater than zero. Example: 5 or 7.5",
    "ad_reward_too_low": "The price is below the minimum for this category. Minimum price: {min_reward} {currency_name}.",
    "ad_send_limit": "Reward per completion: {reward} {currency_name}\n\nHow many completions do you need?",
    "ad_bad_url": "Please send a valid URL or @username.",
    "ad_preview": f"{ce('ads')} Review\n\n├ Type: {{task_type}}\n├ Title: {{title}}\n├ Audience: {{audience}}\n├ Price: {{reward}} {{currency_name}}\n├ Limit: {{limit}}\n└ Total: {{total}} {{currency_name}}\n\n⚠️ Proof screenshots must be reviewed in My tasks.\n\nLaunch?",
    "ad_created": f"{ce('success')} Task #{{task_id}} created. Charged {{total}} {{currency_name}}.",
    "ad_auto": f"{ce('auto_tasks')} Auto tasks\n\nNo channels connected yet. Add a channel to configure automatic promotion for new posts.",
    "ad_auto_add": "Add the bot as channel admin, then connect the channel in the next setup version.",
    "ad_mine": f"{ce('my_tasks')} <b>My tasks</b>\n\n<b>Summary:</b>\n├ Active: {{active}}\n├ Moderation: {{moderation}}\n├ Archived: {{completed}}\n├ Paused: {{paused}}\n└ Waiting for review: {{pending}}\n\n<b>Recent tasks:</b>\n{{items}}\n\nChoose a task or open requests waiting for your decision.",
    "ad_mine_empty": "You have no created tasks yet.",
    "links": (
        f"{ce('links')} <b>Useful links</b>\n\n"
        "By using the bot, you agree to the service rules and privacy policy.\n\n"
        "Choose the section below."
    ),
    "guide": "Guide: earn, create ads, top up balance, share checks and invite referrals.",
    "rules": (
        f"{ce('warning')} <b>Service rules</b>\n\n"
        "1. By using the bot, the user accepts these rules and agrees to follow them.\n\n"
        "2. The service must not be used for fraud, deceiving users, malware distribution or illegal activity.\n\n"
        "3. Ads that violate law or Telegram rules are forbidden, including 18+, drugs, weapons, extremism, phishing and gambling.\n\n"
        "4. Multi-accounting, bots, fake activity and dishonest reward farming are forbidden.\n\n"
        "5. One user may use only one main account. Bypassing limits is forbidden.\n\n"
        "6. The user is fully responsible for promoted content, channels, groups and bots.\n\n"
        "7. Administration may reject or remove any ad task without explanation.\n\n"
        "8. Rewards are credited only after successful task verification.\n\n"
        "9. Attempts to hack, exploit bugs or gain unfair advantage may lead to account blocking.\n\n"
        "10. If rules are violated, administration may restrict access, cancel balance or block the account without prior notice.\n\n"
        "11. Administration is not responsible for user actions or possible losses related to service usage.\n\n"
        "12. Administration may update these rules at any time. The current version is always available in this section."
    ),
    "privacy_policy": (
        f"{ce('shield')} <b>Privacy policy</b>\n\n"
        "1. By using the bot, the user agrees to this Privacy Policy.\n\n"
        "2. The bot may process public Telegram data required for the service, including Telegram ID, username, profile name and task-related technical data.\n\n"
        "3. Data is used only to operate the bot, credit rewards, verify tasks, prevent fraud and contact users.\n\n"
        "4. Administration does not transfer personal data to third parties except where required by law.\n\n"
        "5. The user must not share account access with third parties and is responsible for account security.\n\n"
        "6. Administration takes reasonable measures to protect user data but cannot guarantee absolute security over the internet.\n\n"
        "7. The user may stop using the service at any time.\n\n"
        "8. Administration may update this Privacy Policy without prior notice. The current version is always available in this section."
    ),
    "op": f"{ce('subscription_check')} Subscription check\n\nAdd the bot as group admin, then configure required channels and actions.",
    "op_groups_empty": "No connected groups yet. Add the bot as group admin and come back.",
    "op_groups": f"{ce('group')} Connected groups\n\n{{items}}",
    "op_group_card": "├ Group: {title}\n├ Status: {enabled}\n├ Required channels: {channels_count}\n└ Action: {action}\n\n{warning_text}",
    "op_channels": f"{ce('channel')} Required channels\n\n{{items}}",
    "op_channel_ask": "Add our bot as an admin to the channel, then send the channel link, username or ID.",
    "op_channel_bad": "I cannot check this channel. Add our bot as a channel admin or check the link/ID.",
    "op_warning": "Current warning:\n\n{warning_text}",
    "op_warning_ask": "Send new warning text.",
    "op_actions": "Choose violation action.",
    "op_whitelist": f"{ce('shield')} Whitelist\n\n{{items}}",
    "op_whitelist_ask": "Send user ID or username.",
    "op_stats": f"{ce('statistics')} Stats\n├ Events: {{checks_total}}\n├ OK: {{checks_ok}}\n├ Failed: {{checks_failed}}\n├ Deleted: {{messages_deleted}}\n├ Restricted: {{restricted}}\n└ Required: {{channels_count}}",
    "op_commands": "Group commands.",
    "op_add_bot": "Send the API token of the bot you want to connect. The token is used only for launch checks and is stored protected.",
    "op_guide": f"{ce('instruction')} Guide: add bot, grant admin rights, add required channels, choose action and enable checking.",
    "stats": f"{ce('statistics')} Stats\n├ Users: {{users}}\n├ Active tasks: {{active_tasks}}\n├ Completions: {{completed}}\n├ Payments: {{payments}}\n└ Complaints: {{complaints}}",
    "no_tasks": "No tasks in this category right now.",
    "task_list": (
        "Choose a task from the list.\n\n"
        "Open its card, follow the link and complete the action. Then return to the task and press Check or send proof if the task requires it.\n\n"
        "Do not unsubscribe or block the bot for 7 days, otherwise the reward may be cancelled.\n\n"
        "Available: {total}\n"
        "Page: {page}/{pages}"
    ),
    "task_card": "Task #{id}\n{title}\n{task_details}",
    "sandbox_topup_done": f"{ce('success')} Sandbox top-up completed: +{{amount}} {{currency_name}}.",
    "language": "Choose interface language.",
    "language_set": "Language saved.",
    "checks": f"{ce('checks')} Checks let you transfer internal balance to other users.",
    "check_created": "Check created:\nhttps://t.me/{bot_username}?start=check_{token}",
    "check_activated": "Check activated.",
    "check_bad": "Check is unavailable or already used.",
    "admin": f"{ce('admin')} Admin panel: stats, manual reviews, complaints and balances.",
    "pending_empty": "No pending reviews.",
}
