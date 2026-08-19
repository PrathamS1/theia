# Slack

Slack is a channel-based messaging platform. With Slack, people can work together more effectively, connect all their software tools and services, and find the information they need to do their best work - all within a secure, enterprise-grade environment.

- **Category:** team chat
- **Auth:** OAUTH2
- **Composio Managed App Available?** Yes
- **Tools:** 167
- **Triggers:** 9
- **Slug:** `SLACK`
- **Version:** 20260721_00

## Frequently Asked Questions

### What does the Composio + Slack integration do?

Composio turns Slack's API into ready-to-use tools that AI agents and automations can call. With the integration you can send and read messages, manage channels, upload files, react to events, search conversations, and more — all through a unified platform. Composio supports two toolkits: **Slack** (authenticate as a user for workspace-level actions) and **Slackbot** (authenticate as a bot for in-channel messaging, app mentions, and slash commands). Developers connect their Slack workspace once and then orchestrate any combination of these actions from their agents or workflows.

### How does Composio handle my Slack data?

Composio executes API calls on behalf of your connected account. All data is encrypted and subject to a 30-day retention policy. Authentication tokens are encrypted at rest and scoped to the permissions you grant during the OAuth flow. For full details on data handling, retention, and third-party data practices, see our [Privacy Policy](https://composio.dev/privacy).

### How do I set up custom OAuth credentials for Slack?

For a step-by-step guide on creating and configuring your own Slack OAuth credentials with Composio, see [How to create OAuth credentials for Slack](https://composio.dev/auth/slack).

### When do users see "This app isn't listed in the Slack Marketplace…"?

When a member of a Slack workspace tries to install a non-Marketplace app.

**How to resolve:** Disable **Require apps from Slack Marketplace** in the workspace's app management settings:

`Settings → Apps & Workflows → App Management Settings`

### Why am I being asked to submit a request during auth?

Because **Require approved apps** is enabled in the workspace's **App Management Settings**. Slack is asking for admin/owner approval before completing the install.

### How can a workspace member complete the connection without asking for permissions or approvals?

Two ways:

- Disable both **Require apps from Slack Marketplace** and **Require approved apps** in the workspace's app management settings.
- Use the workspace's own OAuth app, which is recommended and safest. See [How to create OAuth credentials for Slack](https://composio.dev/auth/slack).

### What is the difference between Slack and Slackbot toolkits?

Slack is for workspace-level API access (channels, files, users) while Slackbot is bot-centric (messaging, interactivity). Slack triggers cover workspace events; Slackbot covers bot entry points like app mentions, DMs, and slash commands. Slack can post as the app; Slackbot posts as the bot user.

### Where can I find Slack's available scopes?

See the [Slack scopes reference](https://docs.slack.dev/reference/scopes/).

### Why am I getting a redirect URI mismatch error?

Update the redirect URL in your Slack App under OAuth & Permissions → Redirect URLs.

### How do I set up Slack event webhooks?

With Composio-managed Slack credentials, the webhook endpoint is already provisioned, so just create the trigger. If you bring your own Slack OAuth app, see [Custom OAuth webhooks](https://docs.composio.dev/docs/setting-up-triggers/custom-oauth-webhooks).

### Why am I getting scope errors on Slack?

Either you're missing a bot scope (add one under OAuth & Permissions) or you have "Insufficient scopes" (ensure all scopes from your auth config are configured in the Slack app).

### What does the `as_user` parameter do in Slack tools?

For the Slack toolkit, set `as_user=True` to post as the authenticated user. For Slackbot, leave it blank (defaults to false). A `missing_charset` error usually means invalid `as_user`, wrong channel ID, or missing required fields.

### Why aren't my Slack triggers working?

See [Triggers](/docs/triggers).

### Slack Marketplace warnings during OAuth

Slack may show a Marketplace warning when the OAuth app is not listed or approved in Slack Marketplace. The OAuth flow can still work if the workspace allows non-Marketplace apps, but workspaces with stricter app policies may require admin approval before the connection can complete.

Composio is working on Marketplace review for the managed Slack app. Until that review is complete, use the workspace's own Slack OAuth app or ask a workspace admin to approve the app if the warning blocks users.

![Slack OAuth consent warning stating that the app is not approved by Slack.](/images/kb/toolkits/slack/slack-marketplace-warning.png)

### Do I have to be a Workspace Owner to install the app?

In some cases — yes. For example, when installing non-Marketplace apps, you'll need to be an owner to install directly and complete the connection. As a member, you'd need to either request approval, or ask the owner to disable **Require approved apps**.

## Tools

### Add call participants

**Slug:** `SLACK_ADD_CALL_PARTICIPANTS`

Registers new participants added to a Slack call.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the call returned by the add method. |
| `users` | string | Yes | The list of users to add as participants in the call. users is a JSON array (formatted as a string) containing information for each user. Each element must include a `slack_id`. For example: `[{"slack_id": "U1H77"}]` or `[{"slack_id": "U1H77"}, {"slack_id": "U2ABC123"}]`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add emoji

**Slug:** `SLACK_ADD_EMOJI`

Adds a custom emoji to a Slack workspace given a unique name and an image URL; subject to workspace emoji limits.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | The URL of the image file to be used as the custom emoji. The image should be accessible via HTTP/HTTPS and meet Slack's emoji requirements (e.g., size, format). Supported formats typically include PNG, GIF, and JPEG. |
| `name` | string | Yes | The desired name for the new custom emoji. This name will be used to invoke the emoji (e.g., if name is 'partyparrot', it's used as ':partyparrot:'). Colons around the name are not required when providing this field. Must use lower-case letters only. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add an emoji alias

**Slug:** `SLACK_ADD_EMOJI_ALIAS`

Adds an alias for an existing custom emoji in a Slack Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | The new alias to be created for the emoji specified in `alias_for` (e.g., `new_emoji_alias`). Colons around the name (e.g., `:my_alias:`) are optional and will be automatically trimmed, along with any leading/trailing whitespace. |
| `alias_for` | string | Yes | The canonical name of the existing custom emoji (e.g., `original_emoji`). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add Enterprise user to workspace

**Slug:** `SLACK_ADD_ENTERPRISE_USER_TO_WORKSPACE`

Adds an Enterprise user to a workspace. Use when you need to assign an existing Enterprise Grid user to a specific workspace with optional guest restrictions.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | The ID of the workspace (e.g., T1234567890) where the user will be added. |
| `user_id` | string | Yes | The ID of the user to add to the workspace. |
| `channel_ids` | string | No | Comma separated values of channel IDs to add user in the new workspace. |
| `is_restricted` | boolean | No | True if user should be added to the workspace as a guest. Guests can access only the channels they are invited to. |
| `is_ultra_restricted` | boolean | No | True if user should be added to the workspace as a single-channel guest. Single-channel guests can only access one channel (plus DMs and Huddles). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add reaction to message

**Slug:** `SLACK_ADD_REACTION_TO_AN_ITEM`

Adds a specified emoji reaction to an existing message in a Slack channel, identified by its timestamp; does not remove or retrieve reactions.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Name of the emoji to add as a reaction (e.g., 'thumbsup'). This is the emoji name without colons. For emojis with skin tone modifiers, append '::skin-tone-X' where X is a number from 2 to 6 (e.g., 'wave::skin-tone-3'). The emoji must already exist in the workspace; custom or non-existent emoji names will fail silently. |
| `channel` | string | Yes | ID of the channel where the message to add the reaction to was posted. |
| `timestamp` | string | Yes | Timestamp of the message to which the reaction will be added. This is a unique identifier for the message, typically a string representing a float value like '1234567890.123456'. Must be the exact message timestamp; permalinks or approximate values will not work. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add a remote file

**Slug:** `SLACK_ADD_REMOTE_FILE`

Adds a reference to an external file (e.g., Google Drive, Dropbox) to Slack for discovery and sharing, requiring a unique `external_id` and an `external_url` accessible by Slack.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Title of the remote file to be displayed in Slack. |
| `filetype` | string | No | File type (e.g., 'pdf', 'docx', 'png') to help Slack display appropriate icons or previews. |
| `external_id` | string | Yes | Unique identifier for the file, defined by the calling application, used for future API references (e.g., updating, deleting). |
| `external_url` | string | Yes | Publicly accessible or permissioned URL of the remote file, used by Slack to access its content or metadata. |
| `preview_image` | string | No | Base64-encoded image (e.g., PNG, JPEG) used as the file's preview in Slack. |
| `indexable_file_contents` | string | No | Plain text content of the file, indexed by Slack for search. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Add a star to an item

**Slug:** `SLACK_ADD_STAR`

Stars a channel, file, file comment, or a specific message in Slack.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | ID of the file to add a star to. |
| `channel` | string | No | ID of the channel to star. If starring a specific message, this is the ID of the channel containing the message, and `timestamp` must also be provided. |
| `timestamp` | string | No | Timestamp of the message to add a star to. This uniquely identifies the message within the specified `channel`. Requires `channel` to also be provided. |
| `file_comment` | string | No | ID of the file comment to add a star to. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Search for channels in Enterprise organization

**Slug:** `SLACK_ADMIN_CONVERSATIONS_SEARCH`

Tool to search for public or private channels in an Enterprise organization. Use when you need to find channels by name, type, or other criteria within an Enterprise Grid workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sort` | string ("relevant" | "name" | "member_count" | "created") | No | Sort method for channel search results. |
| `limit` | integer | No | Maximum number of items to be returned. Must be between 1 - 20 both inclusive. Default is 10. |
| `query` | string | No | Name of the channel to query by. |
| `cursor` | string | No | Set cursor to next_cursor returned by the previous call to list items in the next page. |
| `sort_dir` | string ("asc" | "desc") | No | Sort direction for channel search results. |
| `team_ids` | string | No | Comma separated string of team IDs, signifying the workspaces to search through. |
| `total_count_only` | boolean | No | Only return the total_count of channels. Omits channel data and does not require full admin permissions. |
| `connected_team_ids` | string | No | Comma separated string of encoded team IDs, signifying the external organizations to search through. |
| `search_channel_types` | string ("public" | "private" | "private_exclude" | "im" | "mpim" | "ext_shared" | "org_shared" | "archived" | "exclude_archived" | "multi_workspace" | "org_wide" | "external_shared") | No | The type of channel to include or exclude in the search. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Test Slack API connection

**Slug:** `SLACK_API_TEST`

Tool to check API calling code by testing connectivity and authentication to the Slack API. Use when you need to verify that API credentials are valid and the connection is working properly.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `foo` | string | No | Example property to return in the response. This can be any arbitrary string value to test echo functionality. |
| `error` | string | No | Error response to return. Use this parameter to test error handling by simulating various error responses. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Archive a Slack conversation

**Slug:** `SLACK_ARCHIVE_CONVERSATION`

Archives a Slack conversation by its ID, rendering it read-only and hidden while retaining history, ideal for cleaning up inactive channels; be aware that some channels (like #general or certain DMs) cannot be archived and this may impact connected integrations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | No | ID of the Slack conversation to archive. This ID uniquely identifies a channel (e.g., public, private). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Real-time search

**Slug:** `SLACK_ASSISTANT_SEARCH_CONTEXT`

Search Slack messages, files, channels, and users via Real-time Search API. For queries referencing entities by name (users/channels/files), first resolve with content_types (users/channels/files) to get exact ID. If multiple matches, ask user to clarify before proceeding (e.g. ask for user email).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sort` | string | No | Sort results by 'score' (relevance) or 'timestamp' (chronological). Defaults to score. |
| `after` | integer | No | Unix timestamp. Only return results from after this date. |
| `limit` | integer | No | Maximum number of results per page. Max 20. Defaults to 20. |
| `query` | string | Yes | Search query. Supports both keyword search and natural language questions. Natural language queries (starting with what/where/how or ending with ?) trigger semantic search if available on the workspace. Supports OR operator for multiple terms: "deployment issues with kubernetes OR docker OR terraform". |
| `before` | integer | No | Unix timestamp. Only return results from before this date. |
| `cursor` | string | No | Pagination cursor from a previous response's next_cursor field. |
| `sort_dir` | string | No | Sort direction: 'asc' (ascending) or 'desc' (descending). Defaults to desc. |
| `highlight` | boolean | No | Highlight matching search terms in the results. |
| `modifiers` | string | No | Additional search modifiers in 'modifier:value' format. E.g., 'has:pin before:yesterday is:thread'. |
| `action_token` | string | No | Action token from a Slack event payload. Required when using a bot token. Not needed for user tokens. |
| `include_bots` | boolean | No | Include bot messages in search results. |
| `term_clauses` | array | No | List of search term clauses for conjunctive matching. Results must match every clause specified. Each clause is a string with one or more search terms. |
| `channel_types` | string | No | Comma-separated channel types to include: public_channel, private_channel, mpim, im. Defaults to all channel types. |
| `content_types` | string | No | Comma-separated content types to search: messages, files, channels, users. Defaults to messages. |
| `context_channel_id` | string | No | Provide channel context for the search. Note: this parameter provides a contextual hint but may not strictly filter results to only this channel. To reliably restrict results to a specific channel, use the 'modifiers' parameter with 'in:channel_name' instead. |
| `include_deleted_users` | boolean | No | Include deleted users in search results. Defaults to false. |
| `include_message_blocks` | boolean | No | Return message blocks in the response. |
| `disable_semantic_search` | boolean | No | When true, forces keyword-only search even if the workspace has AI/semantic search available. Use this when SLACK_ASSISTANT_SEARCH_INFO returns is_ai_search_enabled=false, or when you explicitly want keyword matching. |
| `include_context_messages` | boolean | No | Include surrounding messages before and after each result for conversational context. |
| `include_archived_channels` | boolean | No | Include results from archived channels. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Check search capabilities

**Slug:** `SLACK_ASSISTANT_SEARCH_INFO`

Check if semantic (AI-powered) search is available on the Slack workspace. Returns whether natural language queries will trigger semantic search in assistant.search.context calls.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Send message

**Slug:** `SLACK_CHAT_POST_MESSAGE`

(DEPRECATED: use `SLACK_SEND_MESSAGE`) Posts a message to a Slack channel, DM, or private group; requires at least one content field (`markdown_text`, `text`, `blocks`, or `attachments`) — omitting all causes a `no_text` error. Fails with `not_in_channel`, `channel_not_found`, or `channel_is_archived` if the bot lacks access. Body limit ~4000 characters. Rate-limited at ~1 req/sec (HTTP 429, honor `Retry-After`). Not idempotent — duplicate calls post duplicate messages.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | No | DEPRECATED: This sends raw text only, use markdown_text field. Primary textual content. Recommended fallback if using `blocks` or `attachments`. Supports mrkdwn unless `mrkdwn` is `false`. |
| `parse` | string | No | Message text parsing behavior. Set to 'full' to parse as user-typed (auto-links @mentions, #channels). Omit for default behavior (no special parsing). |
| `blocks` | string | No | DEPRECATED: Use `markdown_text` field instead. Block Kit layout blocks for rich/interactive messages. Accepts either a URL-encoded JSON string or a list of block dictionaries. See Slack API Block Kit docs for structure. |
| `mrkdwn` | boolean | No | Controls Slack mrkdwn formatting for the top-level `text` field ONLY. Set to `false` to disable formatting (text appears as-is with literal asterisks, underscores, etc.). Default `true` enables mrkdwn formatting (*bold*, _italic_, etc.). NOTE: This parameter has NO effect on `blocks` or `markdown_text` - block content always uses its own formatting rules. |
| `channel` | string | Yes | ID or name of the channel, private group, or IM channel to send the message to. Can be specified as either 'channel' or 'channel_id'. Do NOT include the '#' prefix (e.g., use 'general' not '#general') - any leading '#' will be automatically stripped. For DMs, use the channel ID returned by SLACK_OPEN_DM (starts with 'D'); usernames, emails, and user IDs are not valid DM targets. IMPORTANT: org-wide (Enterprise Grid) tokens cannot resolve channel names — Slack returns `team_not_found`. Pass the channel ID (e.g., 'C0ABC12345') instead; use SLACK_LIST_ALL_CHANNELS to find IDs. |
| `thread_ts` | string | No | Timestamp (`ts`) of an existing message to make this a threaded reply. Use `ts` of the parent message, not another reply. Example: '1476746824.000004'. |
| `link_names` | boolean | No | Automatically hyperlink channel names (e.g., #channel) and usernames (e.g., @user) in message text. Defaults to `false` for bot messages. |
| `attachments` | string | No | This is Slack's legacy 'secondary attachments' field for adding rich formatting elements like colored sidebars, structured fields, and author info to messages. Pass as a JSON string array. NOT for file/image uploads. To send a message with attachments of files or images, use the 'SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK' instead. |
| `unfurl_links` | boolean | No | Enable unfurling of text-based URLs. Defaults `false` for bots, `true` if `as_user` is `true`. |
| `unfurl_media` | boolean | No | Enable media previews (images, videos) from URLs. Set to `true` (default) to show media previews, `false` to hide them. |
| `markdown_text` | string | No | PREFERRED: Write your message in markdown for nicely formatted display. Supports: headers (# ## ###), bold (**text** or __text__), italic (*text* or _text_), strikethrough (~~text~~), inline code (`code`), code blocks (```), links ([text](url)), block quotes (>), lists (- item, 1. item), dividers (--- or ***), context blocks (:::context with images), and section buttons (:::section-button). IMPORTANT: Use \n for line breaks (e.g., 'Line 1\nLine 2'), not actual newlines. USER MENTIONS: To tag users, use their user ID with <@USER_ID> format (e.g., <@U1234567890>), not username. NOTE: Slack enforces a 50-block limit per message. Very long messages with extensive formatting may exceed this limit. If your message is very long, consider splitting it into multiple shorter messages or using simpler formatting. |
| `reply_broadcast` | boolean | No | If `true` for a threaded reply, also posts to main channel. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Close conversation channel

**Slug:** `SLACK_CLOSE_DM`

Closes a Slack direct message (DM) or multi-person direct message (MPDM) channel, removing it from the user's sidebar without deleting history; this action affects only the calling user's view.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | The ID of the direct message or multi-person direct message channel to close. Example: D1234567890 or G0123456789. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Convert public channel to private

**Slug:** `SLACK_CONVERT_CHANNEL_TO_PRIVATE`

Convert a public Slack channel to private using the Admin API. This is an Enterprise Grid only feature and requires an org-installed user token with admin.conversations:write scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Optional name parameter. Only respected when converting an MPIM (multi-person instant message). |
| `channel_id` | string | Yes | The ID of the public channel to convert to private. Required parameter. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create a reminder

**Slug:** `SLACK_CREATE_A_REMINDER`

Creates a Slack reminder with specified text and time; time accepts Unix timestamps, seconds from now, or natural language (e.g., 'in 15 minutes', 'every Thursday at 2pm').

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | The textual content of the reminder message. |
| `time` | string | Yes | Specifies when the reminder should occur. This can be a Unix timestamp (integer, up to five years from now), the number of seconds until the reminder (integer, if within 24 hours, e.g., '300' for 5 minutes), or a natural language description (string, e.g., "in 15 minutes," or "every Thursday at 2pm", "daily"). For recurring reminders, express the recurrence in this field using natural language (e.g., 'every day at 9am', 'every Monday at 10am'). Natural language is parsed relative to the user's workspace timezone; use Unix timestamps when target timezone is uncertain. |
| `user` | string | No | The ID of the user who will receive the reminder (e.g., 'U012AB3CD4E'). If not specified, the reminder will be sent to the user who created it. NOTE: Setting reminders for other users is no longer supported for user tokens - only bot tokens can set reminders for other users. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create Slack Canvas

**Slug:** `SLACK_CREATE_CANVAS`

Creates a new Slack Canvas with the specified title and optional content.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | No | The title of the canvas to create. If not provided, Slack will generate a default title. |
| `channel_id` | string | No | Optional channel ID (e.g., 'C1234567890'). If provided, the canvas will be automatically added as a tab in this channel with write permissions. |
| `document_content` | object | No | Optional canvas content in Slack's document format. If not provided, creates an empty canvas. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create channel

**Slug:** `SLACK_CREATE_CHANNEL`

Initiates a public or private channel-based conversation in a Slack workspace. Immediately creates the channel; invoke only after explicit user confirmation.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Name of the public or private channel to create Must be lowercase, unique, and contain no spaces or periods; max 80 characters. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `is_private` | boolean | No | Create a private channel instead of a public one |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create a channel-based conversation

**Slug:** `SLACK_CREATE_CHANNEL_BASED_CONVERSATION`

Creates a new public or private Slack channel with a unique name; the channel can be org-wide, or team-specific if `team_id` is given (required if `org_wide` is false or not provided).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Name for the new channel. Must be unique, 80 characters or fewer, lowercase, without spaces or periods, and may contain letters, numbers, and hyphens. |
| `team_id` | string | No | Workspace (team) ID for channel creation (e.g., T123ABCDEFG). Required if `org_wide` is `false` or not set. |
| `org_wide` | boolean | No | Set to `true` to make the channel available org-wide. If `false` or not set, `team_id` is required. |
| `is_private` | boolean | Yes | Set to `true` to make the channel private, or `false` for public. |
| `description` | string | No | Optional description for the channel (e.g., 'Discussion about Q4 marketing strategies'). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create Enterprise team

**Slug:** `SLACK_CREATE_ENTERPRISE_TEAM`

Tool to create an Enterprise team in Slack. Use when you need to create a new team (workspace) within an Enterprise Grid organization. Requires admin.teams:write scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_name` | string | Yes | Team name (for example, Slack Softball Team). This is the display name for the team. |
| `team_domain` | string | Yes | Team domain (for example, slacksoftballteam). This will be part of the team's URL. |
| `team_description` | string | No | Description for the team. Helps users understand the purpose of this team. |
| `team_discoverability` | string ("open" | "closed" | "invite_only" | "unlisted") | No | Enum for team discoverability options. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create Slack List

**Slug:** `SLACK_CREATE_SLACK_LIST`

Creates a new Slack List via `slackLists.create`. Provide a `name` and, optionally, a `description_blocks` description and a `schema` of typed columns. You can instead copy an existing List's structure with `copy_from_list_id` (and its rows via `include_copied_list_records`), or enable task-tracking columns with `todo_mode`. Returns the new List's `list_id`. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | The name (title) of the Slack List to create, e.g. 'Sprint Tasks'. This is shown as the List's title in Slack and is required. |
| `schema` | array | No | Column definitions for the List. Each entry is a column object describing a typed column (its `name`, `type`, and any type-specific options such as `select` choices). Supported column types include `text`, `select`, `user`, `date`, `number`, `checkbox`, and others. Omit to create a List with Slack's default columns. |
| `todo_mode` | boolean | No | Set to true to create the List in to-do mode, which adds Slack's built-in task-tracking columns (such as assignee, due date, and completion status) so the List behaves as a task tracker. |
| `copy_from_list_id` | string | No | ID of an existing Slack List to copy the structure from, e.g. 'F0123456789'. When provided, the new List is created with the same columns as that List. Use `include_copied_list_records` to also copy its rows. |
| `description_blocks` | string | No | Rich text describing the List, shown beneath the title. Slack stores this as Block Kit `rich_text` blocks. For convenience you may pass a plain string (it is wrapped into a `rich_text` block automatically), a single block dict (wrapped in a list), or an already-formed list of blocks (passed through unchanged). Omit to create a List with no description. |
| `include_copied_list_records` | boolean | No | When copying from another List via `copy_from_list_id`, set to true to also copy that List's existing items (rows) into the new List. Has no effect unless `copy_from_list_id` is set. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create Slack List item

**Slug:** `SLACK_CREATE_SLACK_LIST_ITEM`

Creates a new item (row) in a Slack List via `slackLists.items.create`. Set initial cell values with `initial_fields`; text columns require Block Kit `rich_text` (a plain string is wrapped automatically). Optionally duplicate an existing row with `duplicated_item_id` or create a subtask with `parent_item_id`. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `list_id` | string | Yes | ID of the Slack List to add the item (row) to, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |
| `initial_fields` | array | No | Initial cell values for the new row. Each entry is a cell object with a `column_id` and a typed value. Text columns must use Block Kit `rich_text` (the plain `text` property is not accepted on input) — for convenience a cell may instead supply a plain string `text` and it will be wrapped into a `rich_text` block automatically. Other column types use their typed key, e.g. `select`, `user`, `date`, `number`, `checkbox`. For `select`, pass an array of the column's choice VALUES (e.g. `["todo"]`) — Slack does not mint separate per-option IDs. Omit to create an empty row. |
| `parent_item_id` | string | No | ID of an existing item (row) to attach the new row to as a subtask. When provided, the new row is created as a sub-item of that parent. |
| `duplicated_item_id` | string | No | ID of an existing item (row) in this List to copy. When provided, the new row is created as a duplicate of that item; `initial_fields` may still be supplied to override copied values. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Create a Slack user group

**Slug:** `SLACK_CREATE_USER_GROUP`

Creates a new User Group (often referred to as a subteam) in a Slack workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Unique name for the User Group. Must be unique among all User Groups in the workspace. |
| `handle` | string | No | Unique mention handle. Must be unique across channels, users, and other User Groups. Max 21 chars; lowercase letters, numbers, hyphens, underscores only. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `channels` | string | No | Comma-separated encoded channel IDs for default channels, suggested when mentioning or inviting the group. |
| `description` | string | No | Short description for the User Group. |
| `include_count` | boolean | No | Include the User Group's user count in the response. Server defaults to `false` if omitted. |
| `enable_section` | boolean | No | Configure this user group to show as a sidebar section for all group members. Only relevant if group has 1 or more default channels added. |
| `additional_channels` | string | No | Comma-separated encoded channel IDs for which the User Group can custom add usergroup members to. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Customize URL unfurl

**Slug:** `SLACK_CUSTOMIZE_URL_UNFURL`

Customizes URL previews (unfurling) in a specific Slack message using a URL-encoded JSON in `unfurls` to define custom content or remove existing previews.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ts` | string | No | Timestamp of the message to customize URL unfurling for. Must be provided with `channel`, or alternatively provide `unfurl_id` and `source` together. |
| `source` | string | No | Link source: either 'composer' or 'conversations_history'. Must be provided with `unfurl_id`. |
| `channel` | string | No | Channel, private group, or DM channel to send message to. Can be an encoded ID, or a name. Must be provided with `ts`, or alternatively provide `unfurl_id` and `source` together. |
| `unfurls` | string | No | JSON string mapping URLs to custom unfurl content (Slack attachment format or blocks). Pass as a plain JSON string (not URL-encoded). To remove an existing unfurl, provide an empty object for that URL. |
| `metadata` | string | No | JSON object with 'entities' field providing Work Object array. Either `unfurls` or `metadata` is required. Pass as a JSON string. |
| `unfurl_id` | string | No | Link ID to unfurl. Must be provided with `source`. Alternative to using `channel` and `ts` parameters. |
| `user_auth_url` | string | No | URL-encoded custom URL for user authentication with your app to enable unfurling. Used when `user_auth_required` is true. |
| `user_auth_blocks` | string | No | JSON array of structured blocks (URL-encoded) sent as ephemeral authentication invitation. Alternative to `user_auth_message` for richer formatting. Used when `user_auth_required` is true. |
| `user_auth_message` | string | No | Ephemeral message text prompting user authentication with your app for domain-specific unfurling. Used when `user_auth_required` is true and authorization is pending. |
| `user_auth_required` | boolean | No | Set to `true` if user authentication is required to unfurl links for a domain, enabling an authentication flow using `user_auth_url` and `user_auth_message`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete Slack Canvas

**Slug:** `SLACK_DELETE_CANVAS`

Deletes a Slack Canvas permanently and irreversibly. Always confirm with the user before calling this tool.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `canvas_id` | string | Yes | The unique identifier of the canvas to delete |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete a public or private channel

**Slug:** `SLACK_DELETE_CHANNEL`

Permanently and irreversibly deletes a specified public or private channel, including all its messages and files, within a Slack Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | string | Yes | ID of the channel to be permanently deleted. This channel can be public or private. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete a file by ID

**Slug:** `SLACK_DELETE_FILE`

Permanently deletes an existing file from a Slack workspace using its unique file ID; this action is irreversible and also removes any associated comments or shares.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | Yes | ID of the file to delete. Typically obtained when a file is uploaded or listed. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete file comment

**Slug:** `SLACK_DELETE_FILE_COMMENT`

Deletes a specific comment from a file in Slack; this action is irreversible.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the comment to delete. This can be obtained when the comment is created or by listing file comments. |
| `file` | string | Yes | ID of the file to delete a comment from. The file ID can be obtained using the `files.info` method or when a file is shared. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete multiple Slack List items

**Slug:** `SLACK_DELETE_MULTIPLE_SLACK_LIST_ITEMS`

Deletes several items (rows) from a Slack List in one call via `slackLists.items.deleteMultiple`. This operation is ALL-OR-NOTHING: Slack returns a single `{"ok": true}` on success or `{"ok": false, "error": ...}` on failure, with NO per-item result array, so partial state cannot be reported. On failure, treat the whole batch as not deleted and retry the entire batch. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ids` | array | Yes | Array of item (row) IDs to delete from the List in a single call, e.g. ['Rec0123456789', 'Rec9876543210']. IMPORTANT: this operation is ALL-OR-NOTHING. Slack `slackLists.items.deleteMultiple` returns a single `{"ok": true}` on success or `{"ok": false, "error": ...}` on failure, with NO per-item result array — so partial state cannot be reported. If the call fails, treat the entire batch as not deleted and retry the whole batch (do not assume some rows were removed). |
| `list_id` | string | Yes | ID of the Slack List to delete items (rows) from, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. All of the `ids` must belong to this List. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete a Slack reminder

**Slug:** `SLACK_DELETE_REMINDER`

Deletes an existing Slack reminder, typically when it is no longer relevant or a task is completed; this operation is irreversible.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `reminder` | string | Yes | The unique identifier of the reminder to be deleted. This ID is obtained when a reminder is created or listed. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete a message from a chat

**Slug:** `SLACK_DELETES_A_MESSAGE_FROM_A_CHAT`

Deletes a message, identified by its channel ID and timestamp, from a Slack channel, private group, or direct message conversation; the authenticated user or bot must be the original poster.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ts` | string | No | Timestamp of the message to be deleted. Must be the exact Slack message timestamp string with fractional precision, e.g., '1234567890.123456'. Thread replies use their own `ts`; ephemeral messages and certain app-posted messages cannot be deleted via this method even with a valid timestamp. |
| `as_user` | boolean | No | Legacy parameter for classic Slack apps. Pass true to delete the message as the authed user. Bot tokens can only delete messages posted by that bot. This parameter is primarily for legacy apps and is generally not needed with modern bot tokens. |
| `channel` | string | No | The ID of the channel, private group, or direct message conversation containing the message to be deleted. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete scheduled chat message

**Slug:** `SLACK_DELETE_SCHEDULED_MESSAGE`

Deletes a pending, unsent scheduled message from the specified Slack channel, identified by its `scheduled_message_id`.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `as_user` | boolean | No | Pass true to delete the message as the authed user with chat:write:user scope. Bot users in this context are considered authed users. If not provided, defaults to false. |
| `channel` | string | Yes | ID of the channel, private group, or DM conversation where the message is scheduled. |
| `scheduled_message_id` | string | Yes | Unique ID (`scheduled_message_id`) of the message to be deleted; obtained from `chat.scheduleMessage` response. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete Slack List access

**Slug:** `SLACK_DELETE_SLACK_LIST_ACCESS`

Revokes sharing access on a Slack List via `slackLists.access.delete`. Provide the `list_id` and EXACTLY ONE of `channel_ids` or `user_ids` (they are mutually exclusive) to remove access for those channels or users. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `list_id` | string | Yes | ID of the Slack List to revoke sharing access on, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |
| `user_ids` | array | No | IDs of the users to revoke access from, e.g. ['U0123456789']. Mutually exclusive with `channel_ids`: provide EXACTLY ONE of `user_ids` or `channel_ids`. Supplying both, or neither, causes the API to return an `invalid_parameters` error. |
| `channel_ids` | array | No | IDs of the channels to revoke access from, e.g. ['C0123456789']. Mutually exclusive with `user_ids`: provide EXACTLY ONE of `channel_ids` or `user_ids`. Supplying both, or neither, causes the API to return an `invalid_parameters` error. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete Slack List item

**Slug:** `SLACK_DELETE_SLACK_LIST_ITEM`

Deletes an item (row) from a Slack List via `slackLists.items.delete`. Identify the List with `list_id` and the row to remove with `id`. Deletion is permanent and cannot be undone. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the item (row) to delete from the List, e.g. 'Rec0123456789'. This is the item ID returned by create_slack_list_item or when listing the List's items. Deleting an item is permanent and cannot be undone. |
| `list_id` | string | Yes | ID of the Slack List that contains the item (row) to delete, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Delete user profile photo

**Slug:** `SLACK_DELETE_USER_PROFILE_PHOTO`

Deletes the Slack profile photo for the user identified by the token, reverting them to the default avatar; this action is irreversible and succeeds even if no custom photo was set.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Disable a Slack user group

**Slug:** `SLACK_DISABLE_USER_GROUP`

Disables a specified, currently enabled Slack User Group by its unique ID, effectively archiving it by setting its 'date_delete' timestamp; the group is not permanently deleted and can be re-enabled.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `usergroup` | string | Yes | Unique encoded ID of the User Group to disable. |
| `include_count` | boolean | No | If true, include the number of users in the User Group in the response. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Download Slack file

**Slug:** `SLACK_DOWNLOAD_SLACK_FILE`

Tool to download Slack file content and convert it to a publicly accessible URL. Use when you need to retrieve and download files that have been shared in Slack channels or conversations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | Yes | ID of the file to download. This is a required field. File IDs start with 'F' followed by alphanumeric characters (e.g., 'F123ABCDEF0'). |
| `page` | integer | No | Page number of comment results to retrieve. Used for comment pagination. Slack's default is 1 if not provided. `cursor`-based pagination is generally preferred. |
| `count` | integer | No | Number of comments to retrieve per page. Used for comment pagination. Slack's default is 100 if not provided. |
| `limit` | integer | No | The maximum number of comments to retrieve. This is an upper limit, not a guarantee of how many will be returned. Primarily used for comment pagination. |
| `cursor` | string | No | Pagination cursor for retrieving comments. Set to `next_cursor` from a previous response's `response_metadata` to fetch the next page of comments. Essential for navigating through large sets of comments. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Edit Slack Canvas

**Slug:** `SLACK_EDIT_CANVAS`

Edits a Slack Canvas with granular control over content placement. Supports replace, insert (before/after/start/end) operations for flexible content management.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `canvas_id` | string | Yes | The unique identifier of the canvas to edit |
| `operation` | string ("replace" | "insert_after" | "insert_before" | "insert_at_start" | "insert_at_end" | "delete" | "rename") | No | Type of edit operation: 'replace' (replaces entire canvas or specific section if section_id provided), 'insert_after' (inserts content after section_id), 'insert_before' (inserts content before section_id), 'insert_at_start' (prepends content to beginning), 'insert_at_end' (appends content to end), 'delete' (deletes specific section by section_id), 'rename' (renames canvas title using title_content) |
| `section_id` | string | No | Section ID for targeted operations. Required for: 'insert_after', 'insert_before', 'delete'. Optional for: 'replace' (if omitted, replaces entire canvas). Not used for: 'insert_at_start', 'insert_at_end'. Use canvases.sections.lookup method to get section IDs from existing canvas. |
| `title_content` | object | No | The new title for the canvas in markdown format. Required only for 'rename' operation. Supports markdown format including emojis (e.g., ':white_check_mark:'). |
| `document_content` | object | No | The content to add/replace in Slack's document format. Required for all operations except 'delete' and 'rename'. Use canvases.sections.lookup to find section IDs for targeted operations. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Share file public url

**Slug:** `SLACK_ENABLE_PUBLIC_SHARING_OF_A_FILE`

Enables public sharing for an existing Slack file by generating a publicly accessible URL; this action does not create new files. Once enabled, the file is accessible to anyone with the URL — verify intent before sharing sensitive or confidential files.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | Yes | The ID of the file to be shared publicly. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Enable a user group

**Slug:** `SLACK_ENABLE_USER_GROUP`

Enables a disabled User Group in Slack using its ID, reactivating it for mentions and permissions; this action only changes the enabled status and cannot create new groups or modify other properties.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `usergroup` | string | Yes | The unique encoded ID of the User Group to enable. This ID typically starts with 'S'. |
| `include_count` | boolean | No | If true, includes the count of users in the User Group in the response. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### End a call

**Slug:** `SLACK_END_CALL`

Ends an ongoing Slack call, identified by its ID (obtained from `calls.add`), optionally specifying the call's duration.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Unique identifier of the call to be ended, obtained from the `calls.add` method. |
| `duration` | integer | No | Duration of the call in seconds. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### End DND session

**Slug:** `SLACK_END_DND`

Ends the authenticated user's current Do Not Disturb (DND) session in Slack, affecting only DND status and making them available; if DND is not active, Slack acknowledges the request without changing status.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### End snooze

**Slug:** `SLACK_END_SNOOZE`

Ends the current user's snooze mode immediately.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Fetch conversation history

**Slug:** `SLACK_FETCH_CONVERSATION_HISTORY`

Fetches a chronological list of messages and events from a specified Slack conversation, accessible by the authenticated user/bot, with options for pagination and time range filtering. IMPORTANT LIMITATION: This action only returns messages from the main channel timeline. Threaded replies are NOT returned by this endpoint. To retrieve threaded replies, use the SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION action (conversations.replies API) instead. The oldest/latest timestamp filters work reliably for filtering the main channel timeline, but cannot be used to retrieve individual threaded replies - even if you know the exact reply timestamp, setting oldest=latest to that timestamp will return an empty messages array. To get threaded replies: 1. Use this action to get parent messages (which include thread_ts, reply_count, latest_reply fields) 2. Use SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION with the parent's thread_ts to fetch all replies in that thread

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of messages to request in this single Slack API call (1-1000). Defaults to 100. Slack may return fewer than requested, especially for non-Marketplace apps where Slack can cap each page at 15 messages. This action does not internally paginate; use response_metadata.next_cursor in the cursor parameter of a follow-up call to fetch more messages. |
| `cursor` | string | No | Pagination cursor from `response_metadata.next_cursor` of a previous response. Omit this for the first page; pass the returned cursor in a follow-up call to fetch the next page. |
| `latest` | string | No | End of the time range of messages to include in results. Accepts a Unix timestamp or a Slack timestamp (e.g., '1234567890.000000'). NOTE: This filter only applies to main channel messages, not threaded replies. Use SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION to retrieve replies. |
| `oldest` | string | No | Start of the time range of messages to include in results. Accepts a Unix timestamp or a Slack timestamp (e.g., '1234567890.000000'). NOTE: This filter only applies to main channel messages, not threaded replies. Use SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION to retrieve replies. |
| `channel` | string | Yes | The ID of the public channel, private channel, direct message, or multi-person direct message to fetch history from. |
| `inclusive` | boolean | No | When true, includes messages at the exact 'oldest' or 'latest' boundary timestamps in results. When false (default), excludes boundary messages. Only applies when 'oldest' or 'latest' is specified. |
| `include_all_metadata` | boolean | No | Return all metadata associated with messages in the conversation history. When true, includes additional metadata fields that may be present on messages. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Fetch item reactions

**Slug:** `SLACK_FETCH_ITEM_REACTIONS`

Fetches reactions for a Slack message, file, or file comment. Exactly one identifier path must be provided: `channel`+`timestamp`, `file`, or `file_comment`. Mixing identifiers (e.g., providing both `channel`+`timestamp` and `file`) causes errors. If the response omits the `reactions` field, the item has zero reactions.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | File ID. Use instead of channel/timestamp or file comment ID. |
| `full` | boolean | No | If true, returns the complete list of users for each reaction. |
| `channel` | string | No | Channel ID. Required if `timestamp` is provided and no file or file comment ID is given. |
| `timestamp` | string | No | Message timestamp (e.g., '1234567890.123456'). Required if `channel` is provided and no file or file comment ID is given. Thread reply timestamps are tracked separately from the parent message; use the reply's own timestamp to fetch its reactions. |
| `file_comment` | string | No | File comment ID. Use instead of channel/timestamp or file ID. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve conversation replies

**Slug:** `SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION`

Retrieves replies to a specific parent message in a Slack conversation, using the channel ID and the parent message's timestamp (`ts`). Note: The parent message in the response contains metadata (reply_count, reply_users, latest_reply) that indicates expected thread activity. If the returned messages array contains fewer replies than reply_count indicates, check: (1) has_more=true means pagination is needed, (2) recently posted replies may have timing delays, (3) some replies may be filtered by permissions or deleted. The composio_execution_message field will warn about any detected mismatches.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ts` | string | No | Timestamp of the parent message in the thread. Must be an existing message. If no replies, only the parent message itself is returned. Must be the exact full timestamp string of the root/parent message — not a reply's ts, a truncated value, a permalink, or an integer; these silently return wrong results. |
| `limit` | integer | No | Maximum number of messages to return. Fewer may be returned even if more are available. |
| `cursor` | string | No | Pagination cursor from `response_metadata.next_cursor` of a previous response to get subsequent pages. If omitted, fetches the first page. |
| `latest` | string | No | Latest message timestamp in the time range to include results. |
| `oldest` | string | No | Oldest message timestamp in the time range to include results. Must be a UTC-based Slack ts string; incorrect timezone conversion or rounding can produce empty result windows. |
| `channel` | string | No | ID of the conversation (channel, direct message, etc.) to fetch the thread from. Must be a channel ID, not a channel name. Token must have membership in private channels or DMs, otherwise returns empty results or `not_in_channel`/`channel_not_found`. |
| `inclusive` | boolean | No | Whether to include messages with `latest` or `oldest` timestamps in results. Effective only if `latest` or `oldest` is specified. |
| `include_all_metadata` | boolean | No | Return all metadata associated with messages in the thread. When true, includes additional metadata fields that may be present on messages. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Fetch team info

**Slug:** `SLACK_FETCH_TEAM_INFO`

Fetches comprehensive metadata about the current Slack team, or a specified team if the provided ID is accessible.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team` | string | No | The ID of the team to retrieve information for. If omitted, information for the current team (associated with the authentication token) is returned. The token must have permissions to view the specified team, especially for teams accessible via external shared channels. |
| `domain` | string | No | Query by domain instead of team (only when team is null). This only works for domains in the same enterprise as the querying team token. This also expects the domain to belong to a team and not the enterprise itself. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Find channels

**Slug:** `SLACK_FIND_CHANNELS`

Find channels in a Slack workspace by any criteria - name, topic, purpose, or description. Returns channel IDs (C*/G* prefixed) required by most Slack tools — always resolve names to IDs here before passing to other tools. NOTE: This action searches channels and conversations visible to the authenticated user. Empty results may indicate: - No channels match the search query in name, topic, or purpose - The target private channel or DM is not accessible to the authenticated user because they are not a member - The connection lacks required read scopes (channels:read, groups:read, im:read, mpim:read). If empty, retry with exact_match=false or exclude_archived=false to avoid false negatives. In large workspaces, paginate using next_cursor to avoid missing matches. Check 'composio_execution_message' and 'total_channels_searched' in the response for details.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of channels to return (1 to 999). Defaults to 50. Slack recommends no more than 200 results at a time for optimal performance. |
| `query` | string | Yes | Search query to find channels. Searches across channel name, topic, purpose, and description (case-insensitive partial matching). Leading '#' prefix is automatically stripped. |
| `types` | string | No | Comma-separated list of channel types to include: `public_channel`, `private_channel`, `mpim` (multi-person direct message), `im` (direct message). Defaults to public and private channels. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `exact_match` | boolean | No | When true, only return channels whose name exactly matches the query (case-insensitive). Also matches against previous channel names and the 'general' flag. When false, returns partial matches across name, topic, and purpose. Defaults to false. |
| `member_only` | boolean | No | Only return channels the user is a member of. Defaults to false. |
| `exclude_archived` | boolean | No | Exclude archived channels from search results. Defaults to true. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Lookup users by email

**Slug:** `SLACK_FIND_USER_BY_EMAIL_ADDRESS`

Retrieves the Slack user object for an active user by their registered email address; requires the users:read.email OAuth scope. Fails with 'users_not_found' if the email is unregistered, the user is inactive, the account is a guest, or the email is hidden by workspace privacy settings.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | The email address of the user to look up. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Find users

**Slug:** `SLACK_FIND_USERS`

Find users in a Slack workspace by any criteria - email, name, display name, or other text. Includes optimized email lookup for exact email matches. Zero results may reflect email visibility restrictions or workspace policies, not global absence. Repeated calls may trigger HTTP 429; honor the Retry-After header.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | No | Email address to search for. This is a convenience parameter that automatically performs an email-based search. Either email or search_query parameter is required. |
| `limit` | integer | No | Maximum number of users to return (1 to 1000). Slack recommends no more than 200 for optimal performance. Defaults to 50. Large workspaces may require pagination or repeated queries to cover all users. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `exact_match` | boolean | No | When true, only returns users with exact matches on name, display name, real name, first name, last name, or email fields (case-insensitive). For email queries, uses Slack's dedicated email lookup endpoint. When false, allows partial/substring matching. Defaults to false. |
| `include_bots` | boolean | No | Include bot users in search results. Defaults to false. |
| `search_query` | string | No | Search query to find users. Can be a Slack user ID (e.g., 'U012ABCDEF'), email address, or name. For user IDs (starting with 'U' or 'W'), uses Slack's users.info API directly. For email addresses with exact_match=true, uses Slack's email lookup endpoint. For other queries, searches across name, display name, real name, email, first name, last name, and status text (case-insensitive partial matching). Either search_query (or 'query' as alias), or email parameter is required. Name-based queries can return multiple matches — verify exactly one user ID before passing to downstream tools like SLACK_OPEN_DM or SLACK_SEND_MESSAGE; disambiguate using email or real_name fields. |
| `include_locale` | boolean | No | Include the `locale` field for each user. Defaults to `false`. |
| `include_deleted` | boolean | No | Include deleted/deactivated users in search results. Defaults to false. |
| `include_restricted` | boolean | No | Include restricted (guest) users in search results. Defaults to true. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get app permission scopes

**Slug:** `SLACK_GET_APP_PERMISSION_SCOPES`

DEPRECATED: Use SLACK_TEST_AUTH instead. Preflight a Slack token by calling auth.test and returning the token's currently granted OAuth scopes (from response headers) to detect missing permissions before attempting admin actions. Use when you need to verify token capabilities or check for specific scopes before making API calls that require elevated permissions.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `required_scopes` | array | No | Optional list of OAuth scopes to check against the token's granted scopes. If provided, the action will compute and return missing_scopes. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get Audit Action Types

**Slug:** `SLACK_GET_AUDIT_ACTION_TYPES`

Tool to retrieve information about action types available in the Slack Audit Logs API. Use when you need to know which action types can be used to filter audit logs or understand the categories of auditable actions in Slack.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get Audit Schemas

**Slug:** `SLACK_GET_AUDIT_SCHEMAS`

Tool to retrieve object schema information from the Slack Audit Logs API. Use when you need to understand the types of objects returned by audit log endpoints. Returns a list of all object types with descriptions.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Fetch bot user information

**Slug:** `SLACK_GET_BOT_USER`

Fetches information for a specified, existing Slack bot user; will not work for regular user accounts or other integration types.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot` | string | No | The ID of the bot user to retrieve information for. This typically starts with 'B'. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve call information

**Slug:** `SLACK_GET_CALL_INFO`

Retrieves a point-in-time snapshot of a specific Slack call's information.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Unique identifier of the Slack call for which to retrieve information. This ID is typically returned when a call is initiated (e.g., by the `calls.add` method). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get Slack Canvas (Deprecated)

**Slug:** `SLACK_GET_CANVAS`

DEPRECATED: Use SLACK_RETRIEVE_DETAILED_INFORMATION_ABOUT_A_FILE instead. Retrieves a specific Slack Canvas by its ID, including its content and metadata.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number for comment pagination (1-based, max 100). Works with count parameter. |
| `count` | integer | No | Maximum number of comments to return per page (1-1000). Controls pagination of the comments field in the response. |
| `limit` | integer | No | Maximum number of comments to return (alternative to count parameter). Recommended to use 200 or less for cursor-based pagination. |
| `cursor` | string | No | Cursor for pagination of comments. Use the next_cursor value from response_metadata to retrieve the next page. This is the preferred pagination method over page parameter. |
| `canvas_id` | string | Yes | The unique identifier of the canvas to retrieve The app must have access to the canvas; private or restricted canvases are not retrievable even with a valid ID. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get channel conversation preferences

**Slug:** `SLACK_GET_CHANNEL_CONVERSATION_PREFERENCES`

Retrieves conversation preferences (e.g., who can post, who can thread) for a specified channel, primarily for use within Slack Enterprise Grid environments.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | string | Yes | Identifier of the channel for which to retrieve conversation preferences. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get reminder information

**Slug:** `SLACK_GET_REMINDER`

Retrieves detailed information for an existing Slack reminder specified by its ID; this is a read-only operation.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `reminder` | string | Yes | The unique identifier of the reminder to retrieve information for. This ID typically starts with 'Rm'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get remote file

**Slug:** `SLACK_GET_REMOTE_FILE`

Retrieve information about a remote file added to Slack via the files.remote API. Does not work for standard Slack-hosted file uploads.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | Specify a file by providing its ID. |
| `external_id` | string | No | Creator defined GUID for the file. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get Slack List item

**Slug:** `SLACK_GET_SLACK_LIST_ITEM`

Fetches a single item (row) from a Slack List via `slackLists.items.info`. Returns the row's `column_id`-keyed typed values along with metadata about the parent List. Set `include_is_subscribed` to also report whether the calling user is subscribed to the row. Requires a user token with the `lists:read` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the item (row) to fetch from the List, e.g. 'Rec0123456789'. This is the `id` of a row previously returned by create_slack_list_item or a List-items listing call. |
| `list_id` | string | Yes | ID of the Slack List that contains the item (row) to fetch, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |
| `include_is_subscribed` | boolean | No | When true, the returned row's `record` includes an `is_subscribed` flag indicating whether the calling user is subscribed to that item. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve team profile details

**Slug:** `SLACK_GET_TEAM_PROFILE`

Retrieves all profile field definitions for a Slack team, optionally filtered by visibility, to understand the team's profile structure.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `visibility` | string ("all" | "visible" | "hidden") | No | Enum for visibility filter values. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get unread messages from user

**Slug:** `SLACK_GET_UNREAD_MESSAGES_FROM_USER`

Retrieves unread direct messages from a specific user by opening their DM conversation, checking for unread messages, and fetching message history since the last read timestamp. Use this action when you need to check if a specific user has sent unread direct messages to the authenticated user, or when monitoring incoming DMs from particular users. Returns an empty messages array if there are no unread messages from the specified user. Note: This action only works for direct messages (DMs), not channel messages or group conversations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of unread messages to retrieve. Slack API allows up to 999, but defaults to 25 for token efficiency. Increase only when specifically needed. |
| `user_id` | string | Yes | The ID of the user to retrieve unread direct messages from. Must be a valid Slack user ID (format: U followed by alphanumeric characters, e.g., U1234567890). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get team DND status

**Slug:** `SLACK_GET_USER_DND_STATUS`

Retrieves a user's current Do Not Disturb status.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `users` | string | Yes | Comma-separated list of users to fetch Do Not Disturb status for |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve user presence

**Slug:** `SLACK_GET_USER_PRESENCE`

Retrieves a Slack user's current real-time presence (e.g., 'active', 'away') to determine their availability, noting this action does not provide historical data or status reasons.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | The ID of the user to query for presence information. This is a string identifier, typically starting with 'U' or 'W' (e.g., 'U123ABC456'). If not provided, presence information for the authenticated user will be returned. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get workspace connections for channel

**Slug:** `SLACK_GET_WORKSPACE_CONNECTIONS_FOR_CHANNEL`

Tool to get all workspaces a channel is connected to within an Enterprise org. Use when you need to determine which workspaces have access to a specific public or private channel in an Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of items to return per page. Must be between 1 and 1000 inclusive. If omitted, API defaults to a reasonable limit. |
| `cursor` | string | No | Pagination cursor from `next_cursor` in the previous response. Set this to paginate through results. Omit for the first page. |
| `channel_id` | string | Yes | The channel ID to determine connected workspaces within the organization for. Must be a valid Slack channel ID (e.g., C0ACHDEQ3JP). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Fetch workspace settings information

**Slug:** `SLACK_GET_WORKSPACE_SETTINGS`

Retrieves detailed settings for a specific Slack workspace, primarily for administrators in an Enterprise Grid organization to view or audit workspace configurations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | The unique identifier of the Slack team (workspace) for which to fetch settings. This ID typically starts with 'T'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Invite users to a Slack channel

**Slug:** `SLACK_INVITE_USERS_TO_A_SLACK_CHANNEL`

Invites users to an existing Slack channel using their valid Slack User IDs. Response is always HTTP 200; inspect `ok`, `error`, and `errors` fields to confirm users were added.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `force` | boolean | No | When set to true and multiple user IDs are provided, continue inviting the valid ones while disregarding invalid IDs. Default is false. |
| `users` | string | No | Comma-separated string of valid Slack User IDs to invite. Up to 1000 user IDs can be included. |
| `channel` | string | No | ID of the public or private Slack channel to invite users to; must be an existing channel. Typically starts with 'C' (public) or 'G' (private/group). Bot must already be a member of private channels to invite others. Archived channels will cause failure. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Invite users to channel

**Slug:** `SLACK_INVITE_USER_TO_CHANNEL`

Invites users to a specified Slack channel; this action is restricted to Enterprise Grid workspaces and requires the authenticated user to be a member of the target channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_ids` | string | Yes | A comma-separated string of Slack User IDs to invite to the channel. Up to 1000 users can be specified. |
| `channel_id` | string | Yes | The ID of the public or private Slack channel to which users will be invited. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Invite user to workspace

**Slug:** `SLACK_INVITE_USER_TO_WORKSPACE`

Invites a user to a Slack workspace and specified channels by email; use `resend=True` to re-process an existing invitation for a user not yet signed up.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | The email address of the person to be invited to the workspace. |
| `resend` | boolean | No | If true, allows this invitation to be resent if the user hasn't signed up. Defaults to false. |
| `team_id` | string | Yes | The ID of the Slack workspace (e.g., T123ABCDEFG) where the user will be invited. |
| `real_name` | string | No | The full name of the user being invited. |
| `channel_ids` | string | Yes | A comma-separated list of channel IDs (e.g., C1234567890,C0987654321) for the user to join. At least one channel ID must be provided. Channel names are not accepted and will cause errors. |
| `is_restricted` | boolean | No | Specifies if the invited user should be a multi-channel guest. Defaults to false. Multi-channel guests can access only the channels they are invited to, plus any public channels. |
| `custom_message` | string | No | Custom message to include in the invitation email. |
| `guest_expiration_ts` | string | No | Unix timestamp for guest account expiration in the format 'XXXXXXXXXX.XXXXXX' (10-digit seconds followed by 6-digit microseconds, e.g., '1735689600.000000'). Provide only if inviting a guest user and an expiration date is desired. |
| `is_ultra_restricted` | boolean | No | Specifies if the invited user should be a single-channel guest (also known as an ultra-restricted guest). Defaults to false. Single-channel guests can only access one channel (plus DMs and Huddles). |
| `email_password_policy_enabled` | boolean | No | Allow invited user to sign in via email and password. Only available for Enterprise Grid teams via admin invite. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Join conversation by channel id

**Slug:** `SLACK_JOIN_AN_EXISTING_CONVERSATION`

Joins an existing Slack conversation (public channel, private channel, or multi-person direct message) by its ID, if the authenticated user has permission. Joining an already-joined channel returns a non-fatal no-op response. Private or restricted channel joins may fail with a permission error.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | ID of the Slack conversation (public channel, private channel, or multi-person direct message) to join. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Leave conversation channel

**Slug:** `SLACK_LEAVE_A_CONVERSATION`

(DEPRECATED: use `SLACK_LEAVE_CONVERSATION`) Leaves a Slack conversation given its channel ID; fails if leaving as the last member of a private channel or if used on a Slack Connect channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | ID of the conversation to leave (e.g., C1234567890). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Leave conversation channel

**Slug:** `SLACK_LEAVE_CONVERSATION`

Leaves a Slack conversation given its channel ID; fails if leaving as the last member of a private channel or if used on a Slack Connect channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | ID of the conversation to leave (e.g., C1234567890). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List approved apps

**Slug:** `SLACK_LIST_ADMIN_APPS_APPROVED`

Tool to list approved apps for an Enterprise Grid organization or workspace. Use when you need to retrieve the list of apps that have been approved for installation by workspace admins. Requires admin.apps:read scope and a user token from an org owner/admin context.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. Must be between 1 and 1000 (inclusive). |
| `cursor` | string | No | Pagination cursor for retrieving the next page. Set to `next_cursor` returned by the previous call to list items in the next page. |
| `team_id` | string | No | The workspace/team ID to list approved apps for. Required when using an org-level token. |
| `certified` | boolean | No | Filter results to certified apps only. When false, certified apps are excluded from results. Defaults to false if not specified. |
| `enterprise_id` | string | No | The Enterprise Grid organization ID to list approved apps for. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List app requests

**Slug:** `SLACK_LIST_ADMIN_APPS_REQUESTS`

Tool to list pending app installation requests for a team/workspace. Use when you need to see which apps users have requested to install that haven't yet been approved or denied. Requires Enterprise Grid or Business+ plan with admin.apps:read scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. Must be between 1 and 1000 inclusive. Defaults to the API's default if not specified. |
| `cursor` | string | No | Pagination cursor for fetching subsequent pages. Set to `next_cursor` returned by the previous call to list items in the next page. Omit for the first page. |
| `team_id` | string | No | The workspace/team ID to list app requests for. Required for Enterprise Grid organizations using org-level tokens. For workspace-level tokens, this filters to a specific workspace. |
| `certified` | boolean | No | Filter results to certified apps only. When true, only certified apps are returned. When false, certified apps are excluded from results. Defaults to false if not specified. |
| `enterprise_id` | string | No | The Enterprise Grid organization ID to list app requests for. Use to query at the Enterprise level. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List admin emoji

**Slug:** `SLACK_LIST_ADMIN_EMOJI`

List custom emoji across an Enterprise Grid organization. Use when you need to retrieve all custom emoji for an entire Enterprise Grid org (not just a single workspace). Requires admin.teams:read scope and an admin token. For single workspace emoji, use the regular emoji.list method instead.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of items to return. Must be between 1 and 1000 (inclusive). |
| `cursor` | string | No | Pagination cursor from response_metadata.next_cursor of a previous response. Use to fetch the next page of results. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List all channels

**Slug:** `SLACK_LIST_ALL_CHANNELS`

Lists conversations available to the user with various filters and search options. Always use resolved `channel_id` (not display names) for downstream operations, as names may be non-unique. The `created` field in results is a Unix epoch timestamp (UTC). Pagination across large workspaces may return HTTP 429 with a `Retry-After` header; honor the delay and resume from the last successful cursor.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of channels to return per page (1 to 1000). Fewer channels may be returned than requested. This schema defaults to 1 if omitted. |
| `types` | string | No | Comma-separated list of conversation types to include: `public_channel` (regular #channels everyone can join), `private_channel` (invite-only channels), `im` (1-on-1 direct messages), `mpim` (group direct messages with 3+ people). Defaults to `public_channel` if omitted. Private channels, IMs, and MPIMs only appear if the authenticated user/bot is a member and the token has the required scopes; absence from results reflects access limits, not non-existence. |
| `cursor` | string | No | Pagination cursor (from a previous response's `next_cursor`) for the next page of results. Omit for the first page. Loop on `response_metadata.next_cursor` until it is empty to retrieve all channels; stopping early silently omits results. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `exclude_archived` | boolean | No | Excludes archived channels if true. The API defaults to false (archived channels are included). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List all users

**Slug:** `SLACK_LIST_ALL_USERS`

Retrieves a paginated list of all users with profile details, status, and team memberships in a Slack workspace; data may not be real-time. Filter response fields `is_bot`, `is_app_user`, and `deleted` to build human-only rosters. Profile fields like `email` and `phone` may be absent depending on OAuth scopes and workspace privacy settings. Guest/restricted accounts may be omitted based on scopes—do not treat results as a complete directory. High-frequency calls risk HTTP 429; honor the `Retry-After` header and throttle to ~1–2 requests/second. Use stable user IDs rather than display names for mapping. Prefer SLACK_FIND_USERS for targeted lookups; cache results to avoid full-workspace fetches.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of items to return per page; fewer may be returned if the end of the list is reached. Recommended to set a value (e.g., 100) as Slack may error for large workspaces if omitted. |
| `cursor` | string | No | Pagination cursor for fetching subsequent pages. Set to `next_cursor` from a previous response's `response_metadata`. Omit for the first page. Paginate until `next_cursor` is empty—stopping early silently undercounts users. Page size is capped at ~200 users. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `include_locale` | boolean | No | Include the `locale` field for each user. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List approved workspace invite requests

**Slug:** `SLACK_LIST_APPROVED_WORKSPACE_INVITE_REQUESTS`

List all approved workspace invite requests with pagination support. Use to review which invite requests have been approved and the details of each approval. Requires admin.invites:read scope and Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The number of results that will be returned by the API on each invocation. Must be between 1 - 1000, both inclusive. Default is 100 if not specified. |
| `cursor` | string | No | Value of the `next_cursor` field sent as part of the previous API response. Use for pagination to retrieve the next page of results. |
| `team_id` | string | No | ID for the workspace where the invite requests were made. If not provided, lists approved requests across all workspaces in the Enterprise Grid organization. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List authorized teams

**Slug:** `SLACK_LIST_AUTH_TEAMS`

Obtains a paginated list of workspaces your org-wide app has been approved for. Use when you need to discover all workspaces within an organization where the app is installed.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. Must be a positive integer no larger than 1000. Default is 100 if not specified. |
| `cursor` | string | No | Paginate through collections of data by setting the cursor parameter to a next_cursor attribute returned by a previous request's response_metadata. Omit for the first page. |
| `include_icon` | boolean | No | When true, the response returns URIs to the avatar images that represent each workspace. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List available workspaces

**Slug:** `SLACK_LIST_AVAILABLE_WORKSPACES`

List Slack workspaces where both the connection and target user have access. Returns each workspace's team_id and name. Use this when: (1) the user references a workspace by name, (2) a user-specific tool requires team_id and you don't have one, or (3) a user-specific call fails with a team/workspace access error. Match the user's workspace name to a team_id from the results and pass that team_id to subsequent tools. If the name matches zero or multiple workspaces, ask the user to clarify. Only meaningful for org-level installs; single-workspace connections return the workspace only if the specified user's membership is visible to this token.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | Yes | Slack user ID whose Enterprise Grid workspace memberships should be matched against the bot-authorized workspaces, such as U0123456789 or W0123456789. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List Slack Canvases (Deprecated)

**Slug:** `SLACK_LIST_CANVASES`

DEPRECATED: Use SLACK_LIST_FILES_WITH_FILTERS_IN_SLACK instead (pass types="canvas" for equivalent behavior). Lists Slack Canvases with filtering by channel, user, timestamp, and page-based pagination. Uses Slack's files.list API with types=canvas filter. Only canvases accessible to the authenticated app are returned; missing canvases indicate permissions restrictions, not empty data. Use `paging.pages` in the response to determine total pages; iterate `page` with `count` to retrieve all results. Known limitations: - The 'user' filter may return canvases accessible to the specified user, not just canvases they created. - The 'ts_from' and 'ts_to' timestamp filters may not work reliably for canvas types. Consider client-side filtering on the 'created' field in the response if precise date filtering is required.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number for pagination (1-based) |
| `user` | string | No | Optional user ID to filter canvases created by a specific user. Note: This filter may return canvases accessible to the user (not just created by them) due to Slack API behavior with canvas types. |
| `count` | integer | No | Maximum number of canvases to return per page (1-1000) |
| `ts_to` | integer | No | Filter canvases created before this Unix timestamp (inclusive). Pass as integer epoch seconds. Note: This filter may not work reliably for canvas types in the Slack API. |
| `channel` | string | No | Optional channel ID (e.g., 'C1234567890') to filter canvases. Must be a channel ID, not name. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `ts_from` | integer | No | Filter canvases created after this Unix timestamp (inclusive). Pass as integer epoch seconds. Note: This filter may not work reliably for canvas types in the Slack API. |
| `show_files_hidden_by_limit` | boolean | No | Display truncated file metadata for older files when workspace has exceeded file limits. When true, shows metadata for files that would normally be hidden due to workspace storage limits. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List conversations

**Slug:** `SLACK_LIST_CONVERSATIONS`

List conversations (channels/DMs) accessible to a specified user (or the authenticated user if no user ID is provided), respecting shared membership for non-public channels. Returns conversation IDs (C* for channels, G* for group DMs), not display names. Absence of private channels, DMs, or MPIMs from results indicates token scope or membership limits, not that the conversation is nonexistent.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | The ID of the user whose conversations will be listed. If not provided, conversations for the authenticated user are returned. Non-public channels are restricted to those where the calling user (authenticating user) shares membership. |
| `limit` | integer | No | The maximum number of items to return per page. Must be an integer, typically between 1 and 1000 (e.g., 100). If omitted, the API's default limit (often 100) applies. Fewer items than the limit may be returned. |
| `types` | string | No | Comma-separated list of conversation types to include: `public_channel` (regular #channels everyone can join), `private_channel` (invite-only channels), `im` (1-on-1 direct messages), `mpim` (group direct messages with 3+ people). If omitted, all types are included. If omitted, the API defaults to `public_channel` only — explicitly specify all desired types to include private channels, DMs, or MPIMs. For `im` results, only user IDs are returned; use a user-lookup tool to resolve display names. |
| `cursor` | string | No | Pagination cursor for retrieving the next set of results. Obtain this from the `next_cursor` field in a previous response's `response_metadata`. If omitted, the first page is fetched. Must loop on `next_cursor` until it is empty to avoid silently missing conversations. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `exclude_archived` | boolean | No | Set to `true` to exclude archived channels from the list. If `false` or omitted, archived channels are typically included (the API's default behavior for omission will apply, usually including them). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List team custom emojis

**Slug:** `SLACK_LIST_CUSTOM_EMOJIS`

Retrieves all custom emojis for the Slack workspace (image URLs or aliases), not standard Unicode emojis; does not include usage statistics or creation dates.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `include_categories` | boolean | No | Include a list of categories for Unicode emoji and the emoji in each category. When true, the response will include 'categories' and 'categories_version' fields. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List denied workspace invite requests

**Slug:** `SLACK_LIST_DENIED_WORKSPACE_INVITE_REQUESTS`

Tool to list all denied workspace invite requests with details about who denied them and when. Use when you need to review or audit denied invitation requests.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The number of results that will be returned by the API on each invocation. Must be between 1-1000 inclusive. |
| `cursor` | string | No | Value of the next_cursor field sent as part of the previous API response for pagination. Omit for the first page. |
| `team_id` | string | No | ID for the workspace where the invite requests were made. Required for Enterprise Grid organizations. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List Enterprise teams

**Slug:** `SLACK_LIST_ENTERPRISE_TEAMS`

List all teams (workspaces) in a Slack Enterprise Grid organization with pagination support. Use when you need to retrieve team IDs, names, domains, and metadata for all workspaces in an Enterprise. Requires admin.teams:read scope and Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return per page. Must be between 1 - 100 both inclusive. If omitted, the API's default limit applies. Fewer items may be returned. |
| `cursor` | string | No | Set cursor to next_cursor returned by the previous call to list items in the next page. Omit for the first page. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List Slack files

**Slug:** `SLACK_LIST_FILES_WITH_FILTERS_IN_SLACK`

Lists files and their metadata within a Slack workspace, filterable by user, channel, timestamp, or type; returns metadata only, not file content. Results are limited to files visible to the authenticated user — files in private channels or restricted to certain members require appropriate membership and permissions. For large workspaces, check `paging.pages` in the response to determine total pages when paginating.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | string | No | Specifies the page number of the results to retrieve when paginating. Default is 1. |
| `user` | string | No | Filter files created by a single user. Provide the Slack User ID. |
| `count` | string | No | Specifies the number of files to return per page. Default is 100, maximum is 1000. |
| `ts_to` | integer | No | Filter files created before this Unix timestamp (inclusive). |
| `types` | string | No | Filter by file type (comma-separated). Valid types: `all` (everything), `spaces` (Posts/long-form content), `snippets` (code snippets), `images`, `pdfs`, `gdocs` (Google Docs), `zips`. Defaults to 'all'. |
| `channel` | string | No | Filter files appearing in a specific channel, indicated by its Slack Channel ID. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `ts_from` | integer | No | Filter files created after this Unix timestamp (inclusive). |
| `show_files_hidden_by_limit` | boolean | No | Show truncated file info for files hidden due to being too old or if the team owning the file is over the storage limit. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List IDP groups linked to channel

**Slug:** `SLACK_LIST_IDP_GROUPS_LINKED_TO_CHANNEL`

Lists IDP groups that have restricted access to a private Slack channel. Use when you need to see which identity provider groups can access a specific channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | The workspace where the channel exists. Required for channels tied to one workspace, optional for channels shared across an organization. |
| `channel_id` | string | Yes | The channel ID to list IDP groups for. This is the unique identifier for the private channel. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List pending workspace invite requests

**Slug:** `SLACK_LIST_PENDING_WORKSPACE_INVITE_REQUESTS`

Tool to list all pending workspace invite requests. Use when you need to see who has been invited but hasn't joined yet. Requires admin.invites:read scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The number of results that will be returned by the API on each invocation. Must be between 1 and 1000 (both inclusive). If not specified, uses the API's default. |
| `cursor` | string | No | Value of the `next_cursor` field sent as part of the previous API response. Used for pagination to fetch subsequent pages of results. Omit for the first page. |
| `team_id` | string | No | ID for the workspace where the invite requests were made. If not provided, lists requests for all workspaces the token has access to. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List pinned items in a channel

**Slug:** `SLACK_LIST_PINNED_ITEMS`

Retrieves all messages and files pinned to a specified channel; the caller must have access to this channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | The ID of the channel to retrieve pinned items from. This can be a public channel ID, private group ID, or direct message channel ID. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List reminders

**Slug:** `SLACK_LIST_REMINDERS`

Lists all reminders with their details for the authenticated Slack user; returns an empty array if no reminders exist (valid state, not an error). Reminder text is not unique—perform client-side matching on returned objects before extracting a reminder ID for use with SLACK_DELETE_A_SLACK_REMINDER.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List remote files

**Slug:** `SLACK_LIST_REMOTE_FILES`

Retrieve information about a team's remote files.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. |
| `ts_to` | number | No | Filter files created before this timestamp (inclusive). |
| `cursor` | string | No | Paginate through collections of data by setting the cursor parameter to a next_cursor attribute returned by a previous request's response_metadata. Default value fetches the first 'page' of the collection. See pagination for more detail. |
| `channel` | string | No | Filter files appearing in a specific channel, indicated by its ID. |
| `ts_from` | number | No | Filter files created after this timestamp (inclusive). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List Restricted Apps

**Slug:** `SLACK_LIST_RESTRICTED_APPS`

Tool to list restricted apps for an org or workspace. Use when you need to view apps that have been restricted from installation. Requires admin.apps:read scope and appropriate admin permissions.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. Must be between 1 and 1000 (inclusive). If omitted, the API default applies. |
| `cursor` | string | No | Pagination cursor from response_metadata.next_cursor of a previous response. Set to next_cursor returned by the previous call to list items in the next page. |
| `team_id` | string | No | The workspace/team ID to list restricted apps from. Use this to filter by a specific workspace within an Enterprise Grid organization. |
| `certified` | boolean | No | Filter results to certified apps only. When false, certified apps are excluded from results. Defaults to false if not specified. |
| `enterprise_id` | string | No | The Enterprise Grid organization ID to list restricted apps from. Use this to filter by a specific enterprise organization. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List scheduled messages

**Slug:** `SLACK_LIST_SCHEDULED_MESSAGES`

Retrieves a list of pending (not yet delivered) messages scheduled in a specific Slack channel, or across all accessible channels if no channel ID is provided, optionally filtered by time and paginated.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum messages per page (1-1000). Defaults to 100. |
| `cursor` | string | No | Pagination cursor from `response_metadata.next_cursor` of a previous response. Omit for the first page. |
| `latest` | string | No | Latest UNIX timestamp (exclusive) for messages. Defaults to the current time if omitted. |
| `oldest` | string | No | Earliest UNIX timestamp (inclusive) for messages. Defaults to 0 if omitted. |
| `channel` | string | No | ID or name of the channel (public, private, or DM) to list messages for. If omitted, lists for all accessible channels in the workspace. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List Slack List items

**Slug:** `SLACK_LIST_SLACK_LIST_ITEMS`

Lists the rows (items) in a Slack List via `slackLists.items.list`. Each row exposes `column_id`-keyed typed values (e.g. `rich_text`, `select`, `user`, `date`, `number`); the legacy `key`/`value` fields are deprecated. Results are cursor-paginated—you must paginate using `response_metadata.next_cursor` until it is empty, or rows are silently truncated to the first page. Set `archived=true` to return archived rows instead of active ones. Requires a user token with the `lists:read` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of rows (items) to return per page; fewer may be returned if the end of the List is reached. Recommended to set a value (e.g., 100) for large Lists. Use `cursor` to fetch subsequent pages. |
| `cursor` | string | No | Pagination cursor for fetching subsequent pages. Set to `next_cursor` from a previous response's `response_metadata`. Omit for the first page. You MUST paginate until `next_cursor` is empty—stopping early silently truncates the result to only the first page of rows. |
| `list_id` | string | Yes | ID of the Slack List whose rows (items) to fetch, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |
| `archived` | boolean | No | When true, return ARCHIVED rows instead of the active (non-archived) rows. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List starred items

**Slug:** `SLACK_LIST_STARRED_ITEMS`

Lists items starred by a user. Returns classic starred items only — does not reflect Slack's 'saved for later' feature. Use SLACK_SEARCH_MESSAGES or SLACK_SEARCH_ALL for broader saved-content queries.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number of results to return. |
| `count` | integer | No | Number of items to return per page. |
| `limit` | integer | No | The maximum number of items to return. Fewer than the requested number of items may be returned, even if the end of the list hasn't been reached. |
| `cursor` | string | No | Parameter for pagination. Set cursor to the next_cursor attribute returned by the previous request's response_metadata. Continue paginating until next_cursor is empty to retrieve all starred items. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List unread channel messages

**Slug:** `SLACK_LIST_UNREAD_CHANNEL_MESSAGES`

Lists all unread messages in a specified Slack channel for the authenticated user. This action fetches messages that have been posted since the user's last read position in the channel. Use this action when you need to retrieve messages the user hasn't seen yet. The action determines the user's read position and returns all messages posted after that timestamp. Note: This only returns messages from the main channel timeline, not threaded replies. For threaded replies, use SLACK_FETCH_MESSAGE_THREAD_FROM_A_CONVERSATION.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of unread messages to return (1-1000). Defaults to 25. Use pagination cursor for additional messages. |
| `cursor` | string | No | Pagination cursor from response_metadata.next_cursor of a previous response. Omit for the first page. |
| `channel` | string | Yes | The ID of the channel to fetch unread messages from. Must be a channel, private channel, or group DM that the authenticated user is a member of. |
| `include_all_metadata` | boolean | No | Return all metadata associated with messages. When true, includes additional metadata fields. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List all users in a user group

**Slug:** `SLACK_LIST_USER_GROUP_MEMBERS`

Retrieves a list of all user IDs within a specified Slack user group, with an option to include users from disabled groups.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `usergroup` | string | Yes | The encoded ID of the User Group to list users from. This ID is an alphanumeric string. |
| `include_disabled` | boolean | No | Set to `true` to include users from disabled user groups. If omitted, the default Slack API behavior for handling disabled groups (typically excluding them) will apply. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List user groups

**Slug:** `SLACK_LIST_USER_GROUPS`

Lists user groups in a Slack workspace, including user-created and default groups; results for large workspaces may be paginated.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `include_count` | boolean | No | Include the number of users in each user group. Defaults to false. |
| `include_users` | boolean | No | Include the list of user IDs for each user group. Defaults to false. |
| `include_disabled` | boolean | No | Include disabled user groups in the results. Defaults to false. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List user reactions

**Slug:** `SLACK_LIST_USER_REACTIONS`

Lists all reactions added by a specific user to messages, files, or file comments in Slack, useful for engagement analysis when the item content itself is not required. Results are paginated; check `response_metadata.next_cursor` and iterate with the `cursor` parameter to retrieve complete reaction history.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `full` | boolean | No | If true, return the complete reaction list, which may include reactions to deleted items. Significantly inflates payload size; enable only when reactions to deleted items are explicitly needed. |
| `page` | integer | No | Page number of results to return. |
| `user` | string | No | Reactions made by this user. Defaults to the authed user. |
| `count` | integer | No | Number of items to return per page. |
| `limit` | integer | No | Maximum number of items to return; fewer items may be returned. Use with cursor-based pagination. |
| `cursor` | string | No | Pagination cursor. Set to `next_cursor` from a previous response's `response_metadata`. See Slack API pagination documentation for details. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List workspace admins

**Slug:** `SLACK_LIST_WORKSPACE_ADMINS`

Tool to list all admins on a given Slack workspace. Use when you need to identify workspace administrators. Requires Enterprise Grid organization and admin.teams:read scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return per page. Must be between 1 and 1000 (inclusive). Fewer may be returned if the end of the list is reached. |
| `cursor` | string | No | Pagination cursor for fetching subsequent pages. Set to next_cursor from a previous response. Omit for the first page. |
| `team_id` | string | Yes | The ID of the workspace to list admins for. Required for Enterprise Grid organizations. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List workspace owners

**Slug:** `SLACK_LIST_WORKSPACE_OWNERS`

Tool to list all owners on a given Slack workspace. Use when you need to identify workspace ownership or admin structure. Requires admin.teams:read scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of items to return. Must be between 1 and 1000 (inclusive). |
| `cursor` | string | No | Set cursor to next_cursor returned by the previous call to list items in the next page. |
| `team_id` | string | Yes | The workspace ID to list owners for. Required parameter. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### List admin users

**Slug:** `SLACK_LIST_WORKSPACE_USERS`

Retrieves a paginated list of admin users for a specified Slack workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of admin users to retrieve per page. Must be a positive integer. If not specified, defaults to 100. |
| `cursor` | string | No | Pagination cursor for retrieving the next page of results. Pass the `next_cursor` value returned from a previous request to fetch subsequent items. If omitted, the first page is retrieved. |
| `team_id` | string | No | The ID of the Slack workspace (e.g., `T123456789`) from which to list admin users. If omitted when using an org-level token, returns users across the entire Enterprise organization. |
| `is_active` | boolean | No | Filter users by their activity status. Set to true to return only active users, false to return only deactivated users. If omitted, defaults to true (active users only). |
| `only_guests` | boolean | No | When true, returns only guest accounts and their expiration dates for the specified team. Defaults to false. |
| `include_deactivated_user_workspaces` | boolean | No | Only applicable with org-level tokens. When true, returns user workspaces regardless of the user's deactivation status. Defaults to false. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Lookup Canvas Sections

**Slug:** `SLACK_LOOKUP_CANVAS_SECTIONS`

Looks up section IDs in a Slack Canvas for use with targeted edit operations. Section IDs are needed for insert_after, insert_before, delete, and section-specific replace operations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `criteria` | object | Yes | Search criteria to find sections. Use 'contains_text' to search for text within sections. Returns section IDs that match the criteria. |
| `canvas_id` | string | Yes | The unique identifier of the canvas to lookup sections in |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set user presence

**Slug:** `SLACK_MANUALLY_SET_USER_PRESENCE`

(DEPRECATED: use `SLACK_SET_USER_PRESENCE`) Manually sets a user's Slack presence, overriding automatic detection; this setting persists across connections but can be overridden by user actions or Slack's auto-away (e.g., after 10 mins of inactivity).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `presence` | string ("auto" | "away") | Yes | The presence state to set for the user. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Open DM

**Slug:** `SLACK_OPEN_DM`

Opens or resumes a Slack direct message (DM) or multi-person direct message (MPIM) by providing either user IDs or an existing channel ID. Returns `already_open=true` when the DM exists — treat as success and reuse the returned `channel.id` (starts with 'D') for subsequent SLACK_SEND_MESSAGE calls; passing a username, email, or user ID directly to SLACK_SEND_MESSAGE causes `channel_not_found`. Avoid redundant calls when an existing DM channel ID is available.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `users` | string | No | Comma-separated string of user IDs (1 for a DM, or 2-8 for an MPIM) to open/resume a conversation. Order is preserved for MPIMs. Either `channel` or `users` must be provided. Accepts list input (will be converted to comma-separated string). Also accepts `user_ids` as alias. Do not pass emails, display names, or workspace usernames — only Slack user IDs (e.g., `U0123456789`). Do not provide both `users` and `channel` simultaneously. |
| `channel` | string | No | ID or name of an existing DM or MPIM channel to open/resume. Either `channel` or `users` must be provided. |
| `return_im` | boolean | No | If `true`, returns the full DM channel object. Applies only when opening a DM via a single user ID in `users` (not with `channel`). |
| `prevent_creation` | boolean | No | Do not create a direct message or multi-person direct message. This is used to see if there is an existing dm or mpdm. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Pin an item to a channel

**Slug:** `SLACK_PIN_ITEM`

Pins a message to a specified Slack channel; the message must not already be pinned.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | The ID of the channel where the message will be pinned. |
| `timestamp` | string | Yes | Timestamp of the message to pin, in ‘epoch_time.microseconds’ format (e.g., ‘1624464000.000200’). This is required by the Slack pins.add API. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Read Audit Logs

**Slug:** `SLACK_READ_AUDIT_LOGS`

Read Slack Enterprise Grid Audit Logs (logins, admin changes, app installs, channel/privacy changes, etc.) with server-side filters and pagination. Requires Enterprise Grid organization with auditlogs:read scope and a user token (xoxp-...) from an owner/admin context.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `actor` | string | No | User ID of the actor who performed the actions. Filters results to only show actions by this user. |
| `limit` | integer | No | Maximum number of audit log entries to return (max 9999). Fewer entries may be returned if there aren't enough matching results. |
| `action` | string | No | Comma-separated list of action types to filter by (max 30). Examples: 'user_login', 'user_logout', 'channel_created', 'app_installed'. See Slack's Audit Logs API documentation for full list. |
| `cursor` | string | No | Pagination cursor from response_metadata.next_cursor of a previous response. Use to fetch the next page of results. |
| `entity` | string | No | Entity ID that was affected by the actions. Filters results to only show actions affecting this entity. |
| `latest` | integer | No | Unix timestamp (inclusive) of the latest audit log entry to include. Use for time-range filtering. |
| `oldest` | integer | No | Unix timestamp (inclusive) of the oldest audit log entry to include. Use for time-range filtering. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove call participants

**Slug:** `SLACK_REMOVE_CALL_PARTICIPANTS`

Registers participants removed from a Slack call.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the call returned by the add method. |
| `users` | string | Yes | The list of users to remove as participants in the call. users is a JSON array with each user having a `slack_id` or `external_id`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove emoji

**Slug:** `SLACK_REMOVE_EMOJI`

Tool to remove a custom emoji across an Enterprise Grid organization. Use when you need to delete a custom emoji from the entire organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | The name of the emoji to be removed. Colons (`:myemoji:`) around the value are not required, although they may be included. The emoji will be removed across the entire Enterprise Grid organization. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove reaction from item

**Slug:** `SLACK_REMOVE_REACTION_FROM_ITEM`

Removes an emoji reaction from a message, file, or file comment in Slack. Provide exactly one targeting method: channel+timestamp together, file, or file_comment. Mixing methods or omitting all returns invalid_arguments.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | ID of the file to remove the reaction from. |
| `name` | string | Yes | Name of the emoji reaction to remove (e.g., 'thumbsup'), without colons. Must be Slack's canonical emoji name; non-canonical names return a 'no_reaction' error. |
| `channel` | string | No | Channel ID of the message. Required if `timestamp` is provided. |
| `timestamp` | string | No | Timestamp of the message. Required if `channel` is provided. |
| `file_comment` | string | No | ID of the file comment to remove the reaction from. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove remote file

**Slug:** `SLACK_REMOVE_REMOTE_FILE`

Removes the Slack reference to an external file (which must have been previously added via the remote files API), specified by either its `external_id` or `file` ID (one of which is required), without deleting the actual external file.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | Slack-specific file ID. |
| `token` | string | No | Authentication token. |
| `external_id` | string | No | Creator-defined, globally unique ID (GUID) for the file. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove a star from an item

**Slug:** `SLACK_REMOVE_STAR`

Removes a star from a previously starred Slack item (message, file, file comment, channel, group, or DM), requiring identification via `file`, `file_comment`, `channel` (for channel/group/DM), or both `channel` and `timestamp` (for a message).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | ID of the file to unstar. |
| `channel` | string | No | ID of the item (channel, private group, DM) or the message's channel (if `timestamp` is also provided). |
| `timestamp` | string | No | Timestamp of the message to unstar; requires `channel`. |
| `file_comment` | string | No | ID of the file comment to unstar. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove user from conversation

**Slug:** `SLACK_REMOVE_USER_FROM_CONVERSATION`

Removes a specified user from a Slack conversation (channel); the caller must have permissions to remove users and cannot remove themselves using this action.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | The ID of the user to be removed from the conversation. |
| `channel` | string | No | ID of the conversation (channel) to remove the user from. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Remove user from workspace

**Slug:** `SLACK_REMOVE_USER_FROM_WORKSPACE`

Tool to remove a user from a Slack workspace. Use when you need to revoke a user's access to a workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | The ID of the workspace (e.g., T1234567890) from which to remove the user. |
| `user_id` | string | Yes | The ID of the user to remove from the workspace. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Rename a conversation

**Slug:** `SLACK_RENAME_CONVERSATION`

Renames a Slack channel, automatically adjusting the new name to meet naming conventions (e.g., converting to lowercase), which may affect integrations using the old name.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | New name for the conversation. Must be 80 characters or less and contain only lowercase letters, numbers, hyphens, and underscores. |
| `channel` | string | No | ID of the conversation (channel) to rename. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Rename an emoji

**Slug:** `SLACK_RENAME_EMOJI`

Renames an existing custom emoji in a Slack workspace, updating all its instances.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Current name of the custom emoji to be renamed. Colons (e.g., `:current_emoji:`) are optional. |
| `new_name` | string | Yes | Desired new name for the custom emoji. Must be unique within the workspace and adhere to Slack's emoji naming conventions. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Reset user sessions

**Slug:** `SLACK_RESET_USER_SESSIONS`

Tool to wipe all valid sessions on all devices for a given user. Use when you need to force a user to re-authenticate due to security concerns or account changes.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | The ID of the user to wipe sessions for (e.g., U1234567890). |
| `web_only` | boolean | No | Only expire web sessions. Defaults to false if not specified. |
| `mobile_only` | boolean | No | Only expire mobile sessions. Defaults to false if not specified. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Restrict app installation

**Slug:** `SLACK_RESTRICT_APP_INSTALLATION`

Restrict an app for installation on a workspace. Use when you need to prevent an app from being installed on a specific workspace or enterprise organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_id` | string | No | The ID of the app to restrict (e.g., A08U8HZHY0Y). Either app_id or request_id must be provided. |
| `team_id` | string | No | The workspace ID to restrict the app installation for (e.g., T1234567890). Either team_id or enterprise_id must be provided. |
| `request_id` | string | No | The ID of the app installation request to restrict. Either app_id or request_id must be provided. |
| `enterprise_id` | string | No | The enterprise organization ID to restrict the app installation for (e.g., E0984HGHPJ6). Either team_id or enterprise_id must be provided. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve a user's identity details

**Slug:** `SLACK_RETRIEVE_A_USER_S_IDENTITY_DETAILS`

Retrieves the authenticated user's and their team's identity, with details varying based on OAuth scopes (e.g., `identity.basic`, `identity.email`, `identity.avatar`).

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve conversation information

**Slug:** `SLACK_RETRIEVE_CONVERSATION_INFORMATION`

Retrieves metadata for a Slack conversation by ID (e.g., name, purpose, creation date, with options for member count/locale), excluding message content. The `channel` parameter is effectively required. Private channels, DMs, or channels where the app lacks membership may return restricted data; check `is_archived` and `is_member` fields in the response to diagnose access issues. Bulk lookups may trigger HTTP 429 rate limiting; honor the `Retry-After` response header.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | No | The ID of the conversation (channel, direct message, or multi-person direct message) to retrieve information for. Effectively required — omitting this parameter yields no useful data despite being marked optional. |
| `include_locale` | boolean | No | If true, the response will include the locale setting for the conversation. Defaults to false. |
| `include_num_members` | boolean | No | If true, the response will include the number of members in the conversation. Defaults to false. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get conversation members

**Slug:** `SLACK_RETRIEVE_CONVERSATION_MEMBERS_LIST`

Retrieves a paginated list of active member IDs (not names, emails, or presence) for a specified Slack public channel, private channel, DM, or MPIM. Returns only user IDs; use a user-lookup tool to enrich member data.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | The maximum number of members to return per page. Fewer items may be returned than the requested limit, even if more members exist and the end of the list hasn't been reached. |
| `cursor` | string | No | Pagination cursor value for fetching specific pages of results. To retrieve the next page, provide the `next_cursor` value obtained from the `response_metadata` of the previous API call. If omitted or empty, the first page of members is fetched. For more details on pagination, refer to Slack API documentation. Loop by passing `next_cursor` into subsequent calls until `next_cursor` is empty to avoid silently truncating large member lists. |
| `channel` | string | No | ID of the conversation (public channel, private channel, direct message, or multi-person direct message) for which to retrieve the member list. Public channel IDs typically start with 'C', private channels or multi-person direct messages (MPIMs) with 'G', and direct messages (DMs) with 'D'. Channel names are NOT accepted — only IDs. Obtain IDs via SLACK_FIND_CHANNELS or SLACK_LIST_CONVERSATIONS. For private channels and MPIMs, the app must have required scopes and be a member of the conversation, otherwise members may not be returned. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve user DND status

**Slug:** `SLACK_RETRIEVE_CURRENT_USER_DND_STATUS`

Retrieves a Slack user's current Do Not Disturb (DND) status to determine their availability before interaction; any specified user ID must be a valid Slack user ID.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | User ID to fetch DND status for. If not provided, fetches the DND status for the authenticated user. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve detailed file information

**Slug:** `SLACK_RETRIEVE_DETAILED_INFORMATION_ABOUT_A_FILE`

Retrieves detailed metadata and paginated comments for a specific Slack file ID; does not download file content.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | Yes | ID of the file to retrieve information for. This is a required field. |
| `page` | integer | No | Page number of comment results to retrieve. Used for comment pagination. Slack's default is 1 if not provided. `cursor`-based pagination is generally preferred. |
| `count` | integer | No | Number of comments to retrieve per page. Used for comment pagination. Slack's default is 100 if not provided. |
| `limit` | integer | No | The maximum number of comments to retrieve. This is an upper limit, not a guarantee of how many will be returned. Primarily used for comment pagination. |
| `cursor` | string | No | Pagination cursor for retrieving comments. Set to `next_cursor` from a previous response's `response_metadata` to fetch the next page of comments. Essential for navigating through large sets of comments. See [pagination](https://slack.dev) for more details. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve detailed user information

**Slug:** `SLACK_RETRIEVE_DETAILED_USER_INFORMATION`

Retrieves comprehensive information for a valid Slack user ID, excluding message history and channel memberships. Sensitive fields like `email` and `phone` require the `users:read.email` scope and may be silently omitted based on workspace privacy policies.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | The ID of the user to retrieve information for. Must be a Slack user ID (U- or W-prefixed); passing emails, display names, or other non-ID strings returns a `user_not_found` error. |
| `include_locale` | boolean | No | Set to `true` to include the user's locale (e.g., `en-US`) in the response. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve message permalink

**Slug:** `SLACK_RETRIEVE_MESSAGE_PERMALINK_URL`

Retrieves a permalink URL for a specific message in a Slack channel or conversation; the permalink respects Slack's privacy settings.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | The ID of the conversation or channel containing the message. This can be a public channel ID, a private channel ID, a direct message channel ID, or a multi-person direct message channel ID. Must be a channel ID, not a channel name; use SLACK_FIND_CHANNELS to resolve names to IDs. |
| `message_ts` | string | Yes | A message's `ts` value (timestamp), uniquely identifying it within a channel. Example: '1610144875.000600'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Retrieve user profile information

**Slug:** `SLACK_RETRIEVE_USER_PROFILE_INFORMATION`

Retrieves profile information for a specified Slack user (defaults to the authenticated user if `user` ID is omitted); a provided `user` ID must be valid. Sensitive fields like email and phone may be silently omitted if required scopes (e.g., `users:read.email`) are not granted or workspace privacy policies restrict access.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user` | string | No | User ID to retrieve profile information for; defaults to the authenticated user. |
| `include_labels` | boolean | No | Include human-readable labels for custom profile fields. API defaults to false. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Revoke a file's public url

**Slug:** `SLACK_REVOKE_FILE_PUBLIC_SHARING`

Revokes a Slack file's public URL, making it private; this is a no-op if not already public and is irreversible.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | Yes | The ID of the file for which to revoke the public URL. This unique identifier typically starts with 'F'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Start RTM session

**Slug:** `SLACK_RTM_CONNECT`

Starts a Real Time Messaging session and returns a WebSocket URL. Use when you need to establish a persistent RTM connection to receive real-time events from Slack.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `presence_sub` | boolean | No | Only deliver presence events when requested by subscription. See presence subscriptions documentation. |
| `batch_presence_aware` | boolean | No | Batch presence deliveries via subscription. Enabling changes the shape of `presence_change` events. See batch presence documentation. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Start RTM session

**Slug:** `SLACK_RTM_START`

Starts a Real Time Messaging API session for Slack. Use when you need to establish an RTM connection with additional options beyond rtm.connect. Note: RTM API is deprecated; consider Socket Mode for new apps.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `no_latest` | boolean | No | Exclude latest timestamps for channels, groups, and direct messages. When set to true, automatically sets no_unreads to true as well. |
| `mpim_aware` | boolean | No | Returns MPIMs (multiparty instant messages / group DMs) in the API response when set to true. If false or omitted, MPIMs may not be included in the channels list. |
| `no_unreads` | boolean | No | Skip unread counts for each channel. When set to true, the response will not include unread message counts for channels, which can reduce payload size. |
| `presence_sub` | boolean | No | Only deliver presence events when requested by subscription. If true, presence change events will only be delivered for users explicitly subscribed to via the presence_query method. |
| `simple_latest` | boolean | No | Return timestamp only for latest message in each channel. When true, only the message timestamp is returned instead of the full message object, reducing payload size. |
| `include_locale` | boolean | No | Set to true to receive locale for users and channels. When enabled, the response will include locale information for users and channels. |
| `batch_presence_aware` | boolean | No | Batch presence deliveries via subscription. If true, presence change events will be batched for subscribed users instead of delivered individually. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Schedule message

**Slug:** `SLACK_SCHEDULE_MESSAGE`

Schedules a message to a Slack channel, DM, or private group for a future time (`post_at`), requiring `text`, `blocks`, or `attachments` for content; scheduling is limited to 120 days in advance.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | No | This sends raw text only, use markdown_text field for formatting. Primary text of the message; formatting with `mrkdwn` applies. Required if `blocks` and `attachments` are not provided. |
| `parse` | string | No | Message text treatment: `full` for special formatting, `none` otherwise (default). See Slack's `chat.postMessage` docs for options. |
| `blocks` | string | No | **DEPRECATED**: Use `markdown_text` field instead. JSON array of structured blocks as a URL-encoded string for message layout and design. Required if `text` and `attachments` are not provided. |
| `channel` | string | No | Channel, private group, or DM channel ID (e.g., C1234567890) or name (e.g., #general) to send the message to. Bot must be a member of the target channel; missing membership returns `not_in_channel` error. **IMPORTANT:** org-wide (Enterprise Grid) tokens cannot resolve channel names — Slack returns `team_not_found`. Pass the channel ID (e.g., `C0ABC12345`) instead; use SLACK_LIST_ALL_CHANNELS to find IDs. |
| `post_at` | string | No | Unix EPOCH timestamp (integer seconds since 1970-01-01 00:00:00 UTC) for the future message send time. Must be strictly greater than current time (past values return `time_in_past` error). Always convert local times to UTC epoch seconds before use; Slack evaluates in UTC only. |
| `thread_ts` | string | No | Timestamp of the parent message for the scheduled message to be a thread reply. Must be float seconds (e.g., `1234567890.123456`). |
| `link_names` | boolean | No | Pass true to automatically link channel names (e.g., #general) and usernames (e.g., @user). NOTE: This parameter is deprecated by Slack; the linking behavior is primarily controlled by Slack's default message parsing. For explicit control, use the 'parse' parameter instead (set to 'full' to enable auto-linking). |
| `attachments` | string | No | This is Slack's legacy 'secondary attachments' field for adding rich formatting elements like colored sidebars, structured fields, and author info. Pass as a JSON string array. NOT for file/image uploads. To send files or images, use 'SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK' instead. |
| `unfurl_links` | boolean | No | Pass false to disable automatic link unfurling. Defaults to true. NOTE: Due to a known Slack API limitation, this parameter may not be respected for scheduled messages (works correctly for chat.postMessage but may be ignored by chat.scheduleMessage). |
| `unfurl_media` | boolean | No | Pass false to disable automatic media unfurling. Defaults to true. NOTE: Due to a known Slack API limitation, this parameter may not be respected for scheduled messages (works correctly for chat.postMessage but may be ignored by chat.scheduleMessage). |
| `markdown_text` | string | No | **PREFERRED**: Write your scheduled message in markdown for nicely formatted display. Supports headers (#), bold (**text**), italic (*text*), strikethrough (~~text~~), code (```), links ([text](url)), quotes (>), and dividers (---). Your message will be posted with beautiful formatting. |
| `reply_broadcast` | boolean | No | With `thread_ts`, makes reply visible to all in channel, not just thread members. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Get SCIM service provider configuration

**Slug:** `SLACK_SCIM_GET_CONFIG`

Tool to retrieve SCIM service provider configuration from Slack. Use when you need to discover Slack's SCIM API capabilities including supported authentication schemes, bulk operations, filtering, and other service provider features.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Search all content

**Slug:** `SLACK_SEARCH_ALL`

Tool to search all messages and files. Use when you need unified content search across channels and files in one call. Results are scoped to content visible to the authenticated token; missing hits in private or restricted channels reflect permission/membership gaps. Response separates messages and files into distinct sections — explicitly read the files section for document results. Results are index-based and may lag several minutes behind real-time; use SLACK_FETCH_CONVERSATION_HISTORY for near-real-time per-channel coverage. Paginated searches exceeding ~1 req/sec may return HTTP 429 too_many_requests; honor the Retry-After header and resume from the last page.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number of results to return; default is 1. Iterate until total_count or page_count signals completion. |
| `sort` | string | No | Sort by `score` (relevance) or `timestamp` (chronological). |
| `count` | integer | No | Number of results per page; default is 20; max is 100. |
| `query` | string | Yes | Search query supporting Slack search modifiers/booleans. Date modifiers after:, before:, on: are UTC day-based; after: is exclusive, so convert time ranges to explicit UTC dates to avoid boundary gaps — sub-day precision requires client-side filtering by numeric ts. Spaces act as logical AND; omitting in:#channel or date filters makes search workspace-wide and slow. Malformed modifiers (e.g., wrong from: format) silently return zero results. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `sort_dir` | string | No | Sort direction: `asc` or `desc`. |
| `highlight` | boolean | No | If true, search terms are wrapped with markers for client-side highlighting. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Search messages

**Slug:** `SLACK_SEARCH_MESSAGES`

Workspace‑wide Slack message search with date ranges and filters. Use `query` modifiers (e.g., in:#channel, from:@user, before/after:YYYY-MM-DD), sorting (score/timestamp), and pagination.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number for manual pagination control. Cannot be used with auto_paginate - choose either automatic collection OR manual page control, not both. |
| `sort` | string | No | Sort results by `score` (relevance) or `timestamp` (chronological). |
| `count` | integer | No | Without auto_paginate: Number of messages per page (max 100). With auto_paginate: Total messages desired. Set count=500 to get 500 messages with automatic pagination handling. |
| `query` | string | Yes | Search query supporting various modifiers for precise filtering:          **Location Modifiers:**         - `in:#channel-name` - Messages in specific channel         - `in:@username` - Direct messages with user          **User Modifiers:**         - `from:@username` - Messages from specific user         - `from:botname` - Messages from bot          **Content Modifiers:**         - `has:link` - Messages with links         - `has:file` - Messages with files         - `has::star:` - Starred messages         - `has::pin:` - Pinned messages          **Special Characters:**         - `"exact phrase"` - Search exact phrase         - `*wildcard` - Wildcard matching         - `-exclude` - Exclude words          **Combinations:** Mix modifiers with date filters like `"project update" on:2025-09-25 in:#marketing from:@john` |
| `cursor` | string | No | Cursor for cursor-mark pagination. Use `*` for the first call, then use `next_cursor` from the previous response for subsequent calls. This is the modern pagination approach recommended by Slack. Cannot be used with `page` parameter - choose either cursor-based or page-based pagination. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `sort_dir` | string | No | Sort direction: `asc` (ascending) or `desc` (descending). |
| `highlight` | boolean | No | Enable highlighting of search terms in results. |
| `auto_paginate` | boolean | No | When enabled, 'count' becomes the total messages desired instead of per-page limit. System automatically handles pagination to collect the specified total. Cannot be used with 'page' parameter - choose either automatic collection or manual page control. Usage: If you fetched 100 messages but pagination shows 500 total available, set auto_paginate=true and count=500 to get all results at once. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Send ephemeral message

**Slug:** `SLACK_SEND_EPHEMERAL_MESSAGE`

Sends an ephemeral message visible only to the specified `user` in a channel; other channel members cannot see it. Both the bot and the target user must be members of the specified channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | No | The message text to display. Required unless 'blocks' or 'attachments' is provided. When using blocks, this serves as fallback text for notifications. Supports markdown formatting. |
| `user` | string | Yes | User ID of the user to send the ephemeral message to. |
| `parse` | string | No | Controls text parsing behavior. Use 'full' to enable automatic linking of @mentions, #channels, and URLs. Use 'none' to disable special parsing (URLs will still be clickable). Defaults to 'none'. |
| `blocks` | string | No | A JSON-based array of structured blocks, presented as a URL-encoded string. |
| `as_user` | boolean | No | Legacy parameter for authenticated user authorship. Defaults to true without chat:write:bot scope, false otherwise. Setting to true requires chat:write:user scope for the authenticated user to author the message. |
| `channel` | string | Yes | Channel, private group, or DM channel to send message to. Can be an encoded ID, or a name. **IMPORTANT:** org-wide (Enterprise Grid) tokens cannot resolve channel names — Slack returns `team_not_found`. Pass the channel ID (e.g., `C0ABC12345`) instead; use SLACK_LIST_ALL_CHANNELS to find IDs. |
| `icon_url` | string | No | URL to an image to use as the icon for this message. Must be used in conjunction with as_user set to false, otherwise ignored. See authorship below. |
| `username` | string | No | Set your bot's user name. Must be used in conjunction with as_user set to false, otherwise ignored. See authorship below. |
| `thread_ts` | string | No | Provide another message's ts value to make this message a reply. Avoid using a reply's ts value; use its parent instead. |
| `icon_emoji` | string | No | Emoji to use as the icon for this message. Overrides icon_url. Must be used in conjunction with as_user set to false, otherwise ignored. See authorship below. |
| `link_names` | boolean | No | Find and link channel names and usernames. |
| `attachments` | string | No | This is Slack's legacy 'secondary attachments' field for adding rich formatting elements like colored sidebars, structured fields, and author info. Pass as a JSON string array. NOT for file/image uploads. To send files or images, use 'SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK' instead. |
| `markdown_text` | string | No | PREFERRED: Write your ephemeral message in markdown for nicely formatted display. Supports: headers (# ## ###), bold (**text** or __text__), italic (*text* or _text_), strikethrough (~~text~~), inline code (`code`), code blocks (```), links ([text](url)), block quotes (>), lists (- item, 1. item), dividers (--- or ***). IMPORTANT: Use \n for line breaks (e.g., 'Line 1\nLine 2'), not actual newlines. Incompatible with blocks or text parameters. Maximum 12,000 characters. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Share a me message in a channel

**Slug:** `SLACK_SEND_ME_MESSAGE`

Sends a 'me message' (e.g., '/me is typing') to a Slack channel, where it's displayed as a third-person user action; messages are plain text and the channel must exist and be accessible.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | No | Content of the 'me message', displayed as an action performed by the user (e.g., if text is 'is feeling happy', it appears as '*User is feeling happy*'). |
| `channel` | string | No | Specifies the target channel by its public ID (e.g., 'C1234567890'), private group ID, IM channel ID, or name (e.g., '#general', '@username'). **IMPORTANT:** org-wide (Enterprise Grid) tokens cannot resolve channel names — Slack returns `team_not_found`. Pass the channel ID (e.g., `C0ABC12345`) instead; use SLACK_LIST_ALL_CHANNELS to find IDs. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Send message

**Slug:** `SLACK_SEND_MESSAGE`

Posts a message to a Slack channel, DM, or private group. Provide exactly one visible content mode: `markdown_text` for normal Markdown content, or `blocks` for raw Slack Block Kit layouts. Use `fallback_text` only with `blocks`; it maps to Slack's top-level `text` fallback. Fails with `not_in_channel`, `channel_not_found`, or `channel_is_archived` if the bot lacks access. Rate-limited at ~1 req/sec (HTTP 429, honor `Retry-After`). Not idempotent — duplicate calls post duplicate messages.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `blocks` | array | No | Use this instead of `markdown_text` only when you need Slack Block Kit capabilities that Markdown cannot express: buttons, approval/reject actions, select menus, checkboxes, radio buttons, date/time pickers, overflow menus, interactive workflow payloads, section accessories, image/video blocks, context rows, two-column fields, multiple action buttons in one row, or rich card-like layouts. Provide raw Slack Block Kit JSON as an array. For normal prose generated by an LLM inside a blocks payload, prefer a Slack markdown block: {'type': 'markdown', 'text': '# Heading\n\nBody text'}. Do not use this together with `markdown_text`. If these blocks are the visible content, provide `fallback_text` when notification/accessibility fallback matters. |
| `channel` | string | Yes | ID or name of the channel, private group, or IM channel to send the message to. Can be specified as either 'channel' or 'channel_id'. Do NOT include the '#' prefix (e.g., use 'general' not '#general') - any leading '#' will be automatically stripped. For DMs, use the channel ID returned by SLACK_OPEN_DM (starts with 'D'); usernames, emails, and user IDs are not valid DM targets. IMPORTANT: org-wide (Enterprise Grid) tokens cannot resolve channel names — Slack returns `team_not_found`. Pass the channel ID (e.g., 'C0ABC12345') instead; use SLACK_LIST_ALL_CHANNELS to find IDs. |
| `thread_ts` | string | No | Timestamp (`ts`) of an existing message to make this a threaded reply. Use `ts` of the parent message, not another reply. Example: '1476746824.000004'. |
| `unfurl_links` | boolean | No | Enable unfurling of text-based URLs. Defaults `false` for bots, `true` if `as_user` is `true`. |
| `unfurl_media` | boolean | No | Enable media previews (images, videos) from URLs. Set to `true` (default) to show media previews, `false` to hide them. |
| `fallback_text` | string | No | Optional only when using `blocks`. Maps to Slack's top-level `text` field for notifications, accessibility, search previews, and clients that cannot render blocks. This should be a short plain-text summary of the block content, not another visible message body. Omit it if you want Slack to infer fallback text from supported blocks. |
| `markdown_text` | string | No | Use this for normal LLM-written message content. Pass standard Markdown exactly as written; this tool sends it to Slack's native `markdown_text` argument without converting it to blocks. Do not use this together with `blocks`. Supports Slack's native markdown handling for headings, bold, italic, links, lists, code, quotes, dividers, tables, and task lists. Slack collapses literal empty Markdown lines; to force visible blank spacer rows, put a non-breaking space on each spacer line, e.g. `a\n\u00a0\n\u00a0\n\u00a0\nb`. For Slack mentions, use explicit entity syntax such as <@USER_ID>, <#CHANNEL_ID>, or <!subteam^GROUP_ID>; do not rely on @name or #name auto-linking. Use `blocks` instead when you need buttons, selects, checkboxes, image blocks, context rows, fields, accessories, or other interactive/layout controls. |
| `reply_broadcast` | boolean | No | If `true` for a threaded reply, also posts to main channel. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set admin user

**Slug:** `SLACK_SET_ADMIN_USER`

Promotes an existing workspace member (guest, regular user, or owner) to admin status. Use when you need to grant admin privileges to a user.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | The ID of the workspace (e.g., T1234567890) where the user will be set as admin. This uniquely identifies the Slack workspace. |
| `user_id` | string | Yes | The ID of the user (e.g., U1234567890) to designate as an admin. This user must be an existing member of the workspace (guest, regular user, or owner). |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set conversation preferences

**Slug:** `SLACK_SET_CONVERSATION_PREFS`

Sets the posting permissions for a public or private channel in Slack. Use this to control who can post messages, start threads, use @channel/@here mentions, and initiate huddles in a specific channel.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prefs` | string | Yes | The prefs for this channel in a stringified JSON format. Example: '{"who_can_post":"type:admin"}' to restrict posting to admins only, or '{"who_can_post":{"type":["admin","ra"]}}' to allow admins and regular users. The prefs object can include: who_can_post (defines who can post messages), can_thread (defines who can respond in threads), can_huddle (boolean), enable_at_channel (object with 'enabled' boolean), enable_at_here (object with 'enabled' boolean). |
| `channel_id` | string | Yes | The channel to set the prefs for. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set a conversation's purpose

**Slug:** `SLACK_SET_CONVERSATION_PURPOSE`

Sets the purpose (a short description of its topic/goal, displayed in the header) for a Slack conversation; the calling user must be a member.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | No | The ID of the conversation (channel, direct message, or group message) to set the purpose for. |
| `purpose` | string | No | The new purpose for the conversation. This text will be displayed as the channel description. The maximum length is 250 characters. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set default channels

**Slug:** `SLACK_SET_DEFAULT_CHANNELS`

Tool to set the default channels of a workspace. Use when you need to configure which channels new members automatically join.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | ID for the workspace to set the default channel for. |
| `channel_ids` | string | Yes | A list of channel IDs to set as default channels. Can also accept a comma-separated string for backwards compatibility. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set DND duration

**Slug:** `SLACK_SET_DND_DURATION`

Turns on Do Not Disturb mode for the current user, or changes its duration.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `num_minutes` | string | Yes | Number of minutes, from now, to snooze until. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set profile photo

**Slug:** `SLACK_SET_PROFILE_PHOTO`

This method allows the user to set their profile image.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image` | object | Yes | Profile image file to upload. Maximum 1024x1024 pixels, minimum 512x512 pixels recommended. |
| `crop_w` | integer | No | Width/height of crop box (always square) |
| `crop_x` | integer | No | X coordinate of top-left corner of crop box |
| `crop_y` | integer | No | Y coordinate of top-left corner of crop box |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set conversation read cursor

**Slug:** `SLACK_SET_READ_CURSOR_IN_A_CONVERSATION`

Marks a message, specified by its timestamp (`ts`), as the most recently read for the authenticated user in the given `channel`, provided the user is a member of the channel and the message exists within it.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ts` | string | No | The timestamp of the message to mark as the most recently read. Must be a Slack timestamp string with microsecond precision in the format 'UNIX_TIMESTAMP.MICROSECONDS' (e.g., '1625800000.000200'). |
| `channel` | string | No | The ID of the public channel, private channel, or direct message to set the read cursor for. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set Slack List access

**Slug:** `SLACK_SET_SLACK_LIST_ACCESS`

Grants or sets sharing access on a Slack List via `slackLists.access.set`. Grant `read`, `write`, or `owner` access to either channels (`channel_ids`) or users (`user_ids`) — exactly one of the two is required. The `owner` level is user-only and subject to additional server-side rules. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `list_id` | string | Yes | ID of the Slack List to set sharing access on, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |
| `user_ids` | array | No | IDs of the users to grant access to. Mutually exclusive with `channel_ids`: EXACTLY ONE of `channel_ids` or `user_ids` is required — supplying both or neither returns `invalid_parameters` from the API. Required when the `access_level` is `owner`. |
| `channel_ids` | array | No | IDs of the channels to grant access to. Mutually exclusive with `user_ids`: EXACTLY ONE of `channel_ids` or `user_ids` is required — supplying both or neither returns `invalid_parameters` from the API. Cannot be combined with the `owner` access level. |
| `access_level` | string | Yes | The access level to grant on the List. One of `read`, `write`, or `owner`. `read` grants view-only access; `write` grants edit access. `owner` is USER-ONLY: it must be paired with `user_ids` (not `channel_ids`) — supplying `channel_ids` together with `owner` returns `invalid_arguments` from the API. Only the List's current owner can assign the `owner` level, and cross-team owner upgrades are disallowed. The exactly-one-target rule and the `owner`->`user_ids` requirement are validated client-side here; the ownership/cross-team rules remain enforced server-side by Slack. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set Slack user profile information

**Slug:** `SLACK_SET_STATUS`

(DEPRECATED: use `SLACK_SET_USER_PROFILE`) Updates a Slack user's profile, setting either individual fields or multiple fields via a JSON object.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Name of a single profile field to set. Use with `value` if `profile` is not provided. |
| `user` | string | No | ID of the user whose profile will be updated; defaults to authenticated user. Team admins on paid teams can specify another member's ID. |
| `value` | string | No | Value for the single profile field specified by `name`. Use with `name` if `profile` is not provided. |
| `profile` | string | No | JSON string of key-value pairs for profile fields to update (max 50 fields, 255 chars per field name). Pass as a plain JSON string (not URL-encoded). If provided, `name` and `value` are ignored. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set conversation topic

**Slug:** `SLACK_SET_THE_TOPIC_OF_A_CONVERSATION`

Sets or updates the topic for a specified Slack conversation.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | No | The new topic for the conversation. It must be a string up to 250 characters long. Text formatting and linkification are not supported. |
| `channel` | string | No | The ID of the public channel, private channel, direct message, or multi-person direct message conversation for which the topic will be set. Must be a channel ID (C/G/D prefix), not a human-readable name like '#general'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Mark user as active

**Slug:** `SLACK_SET_USER_ACTIVE`

Tool to mark a user as active in Slack. Note: This endpoint is deprecated and non-functional - it exists for backwards compatibility but does not perform any action.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set user presence

**Slug:** `SLACK_SET_USER_PRESENCE`

Manually sets a user's Slack presence, overriding automatic detection; this setting persists across connections but can be overridden by user actions or Slack's auto-away (e.g., after 10 mins of inactivity).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `presence` | string ("auto" | "away") | Yes | The presence state to set for the user. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set Slack user profile information

**Slug:** `SLACK_SET_USER_PROFILE`

Updates a Slack user's profile, setting either individual fields or multiple fields via a JSON object.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Name of a single profile field to set. Use with `value` if `profile` is not provided. |
| `user` | string | No | ID of the user whose profile will be updated; defaults to authenticated user. Team admins on paid teams can specify another member's ID. |
| `value` | string | No | Value for the single profile field specified by `name`. Use with `name` if `profile` is not provided. |
| `profile` | string | No | JSON string of key-value pairs for profile fields to update (max 50 fields, 255 chars per field name). Pass as a plain JSON string (not URL-encoded). If provided, `name` and `value` are ignored. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set workspace description

**Slug:** `SLACK_SET_WORKSPACE_DESCRIPTION`

Set the description of a given workspace. Use when you need to update or change the description text displayed for a Slack workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | ID for the workspace to set the description for. |
| `description` | string | Yes | The new description for the workspace. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set workspace icon

**Slug:** `SLACK_SET_WORKSPACE_ICON`

Sets the icon of a workspace. Use when you need to update or change the workspace icon image. The image must be publicly accessible and in a supported format (GIF, PNG, JPG, JPEG, HEIC, or HEIF).

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | ID of the workspace to set the icon for. |
| `image_url` | string | Yes | Publicly accessible URL of the image to set as the workspace icon. Must be in GIF, PNG, JPG, JPEG, HEIC, or HEIF format. Ideally 512x512 pixels for best display quality. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set workspace name

**Slug:** `SLACK_SET_WORKSPACE_NAME`

Set the name of a given Slack workspace. Use when you need to update the display name for a workspace in an Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | The new name of the workspace. |
| `team_id` | string | Yes | ID for the workspace to set the name for. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set workspace owner

**Slug:** `SLACK_SET_WORKSPACE_OWNER`

Set an existing guest, regular user, or admin user to be a workspace owner. Use when you need to promote a workspace member to owner status. Requires an Enterprise Grid workspace.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | The ID of the workspace or organization (e.g., T1234567890). This specifies which workspace the user should become an owner of. Must be an Enterprise Grid workspace. |
| `user_id` | string | Yes | The ID of the user to promote to workspace owner (e.g., U1234567890). The user must already be a member, guest, or admin of the workspace. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Set workspaces for channel

**Slug:** `SLACK_SET_WORKSPACES_FOR_CHANNEL`

Set the workspaces in an Enterprise grid org that connect to a channel. Use when you need to share a public or private channel with specific workspaces in an Enterprise Grid organization.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | No | The workspace to which the channel belongs. Omit this argument if the channel is a cross-workspace shared channel. |
| `channel_id` | string | Yes | The encoded channel ID to add or remove to workspaces. |
| `org_channel` | boolean | No | True if channel has to be converted to an org channel. |
| `target_team_ids` | string | No | A comma-separated list of workspaces to which the channel should be shared. Not required if the channel is being shared org-wide. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Share a remote file in channels

**Slug:** `SLACK_SHARE_REMOTE_FILE`

Shares a remote file, which must already be registered with Slack, into specified Slack channels or direct message conversations.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | The unique ID of the remote file registered with Slack. Either this `file` field or the `external_id` field (or both) is required to identify the file. |
| `channels` | string | Yes | A comma-separated list of channel IDs where the remote file will be shared. These can include public channel IDs, private channel IDs, or direct message channel IDs. |
| `external_id` | string | No | The globally unique identifier (GUID) for the remote file, as provided by the app that registered it with Slack. Either this `external_id` field or the `file` field (or both) is required to identify the file. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Start call

**Slug:** `SLACK_START_CALL`

Registers a new call in Slack using `calls.add` for third-party call integration; `created_by` is required if not using a user-specific token.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | No | The name or title for the call. This will be displayed in Slack to identify the call. |
| `users` | string | No | A JSON string representing an array of user objects to be registered as participants in the call. Each user object in the array should define a participant using their `slack_id` (Slack User ID) and/or an `external_id` (an identifier from the third-party application, unique to that user within that application). For instance: `'''[{"slack_id": "U012A3BCD4E"}, {"external_id": "user-xyz@example.com", "slack_id": "U012A3BCD4F"}]'''`. |
| `join_url` | string | Yes | The URL required for a client to join the call (e.g., a web join link). This field is mandatory. Must be a valid third-party call system URL (e.g., web join link), not a Slack channel or message URL. |
| `created_by` | string | No | Slack user ID of the creator; optional (defaults to authenticated user) if using a user token, otherwise required. |
| `date_start` | integer | No | The start time of the call, specified as a UTC UNIX timestamp in seconds. For example, `1678886400` corresponds to March 15, 2023, at 12:00 PM UTC. |
| `external_unique_id` | string | Yes | A unique identifier for the call, supplied by the third-party call provider. This ID must be unique across all calls from that specific service. This field is required. |
| `external_display_id` | string | No | An optional, human-readable identifier for the call, supplied by the third-party call provider. If provided, this ID will be displayed in the Slack call object interface. |
| `desktop_app_join_url` | string | No | An optional URL that, when provided, allows Slack clients to attempt to directly launch the third-party call application. This is typically a deep link URI for the specific application. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Test authentication

**Slug:** `SLACK_TEST_AUTH`

Checks authentication and tells you who you are. Use to verify Slack API authentication is functional and to retrieve identity information about the authenticated user or bot.

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Unarchive channel

**Slug:** `SLACK_UNARCHIVE_CHANNEL`

Reverses conversation archival.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | ID of conversation to unarchive |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Unpin message from channel

**Slug:** `SLACK_UNPIN_ITEM`

Unpins a message, identified by its timestamp, from a specified channel if the message is currently pinned there; this operation is destructive.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel` | string | Yes | The ID of the channel where the message is pinned (e.g., a public channel, private channel, or direct message). |
| `timestamp` | string | Yes | Timestamp of the message to unpin. This is required to identify the specific message to be removed from the channel's pinned items. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update call information

**Slug:** `SLACK_UPDATE_CALL_INFO`

Updates the title, join URL, or desktop app join URL for an existing Slack call identified by its ID.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Unique identifier of the call to update, obtained when a call is created (e.g., via `calls.add` Slack API method). |
| `title` | string | No | New title for the call. |
| `join_url` | string | No | New URL for clients to join the call. |
| `desktop_app_join_url` | string | No | URL to directly launch the third-party call application from Slack clients. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update an existing remote file

**Slug:** `SLACK_UPDATE_REMOTE_FILE`

Updates metadata or content details for an existing remote file in Slack; this action cannot upload new files or change the fundamental file type.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | Slack's unique identifier for the remote file (e.g., `F12345678`). Used to identify the file if `external_id` is not provided. One of `file` or `external_id` is required to specify the file to update. |
| `title` | string | No | New title for the remote file. If omitted, the current title remains unchanged. |
| `token` | string | No | Authentication token for authorizing the API request to Slack. |
| `filetype` | string | No | New filetype for the remote file. This typically describes the kind of file, e.g., `pdf`, `gdoc`, `image`, `text`. See Slack API documentation for specific supported `filetype` values. Providing an inaccurate filetype might affect how the file is handled or displayed. |
| `external_id` | string | No | Creator-defined Globally Unique Identifier (GUID) for the remote file. Used to identify the file if `file` ID is not provided. One of `file` or `external_id` is required to specify the file to update. |
| `external_url` | string | No | New publicly accessible URL for the remote file. If provided, this updates the link associated with the file in Slack. |
| `preview_image` | string | No | A string that references the new preview image for the document. The referenced image data will be sent as `multipart/form-data`. This could be a local file path (if supported by the client), a public URL, or base64 encoded image data. Max 1MB. Updates the file's preview in Slack. |
| `indexable_file_contents` | string | No | Plain text content extracted from the remote file, used by Slack to improve searchability. This can be a summary or the full text. Maximum 1MB. If provided, updates the searchable content. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update a Slack message

**Slug:** `SLACK_UPDATES_A_SLACK_MESSAGE`

Updates a Slack message by timestamp. Provide exactly one visible content mode: `markdown_text` for normal Markdown content, or `blocks` for raw Slack Block Kit layouts. Use `fallback_text` only with `blocks`; it maps to Slack's top-level `text` fallback.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ts` | string | Yes | Timestamp of the message to update (string, Unix time with microseconds, e.g., `'1234567890.123456'`). |
| `blocks` | array | No | Use this instead of `markdown_text` only when updating to Slack Block Kit capabilities that Markdown cannot express: buttons, approval/reject actions, select menus, checkboxes, radio buttons, date/time pickers, overflow menus, interactive workflow payloads, section accessories, image/video blocks, context rows, two-column fields, multiple action buttons in one row, or rich card-like layouts. Provide raw Slack Block Kit JSON as an array. For normal prose generated by an LLM inside a blocks payload, prefer a Slack markdown block: {'type': 'markdown', 'text': '# Heading\n\nBody text'}. Do not use this together with `markdown_text`. If these blocks are the visible content, provide `fallback_text` when notification/accessibility fallback matters. |
| `as_user` | boolean | No | Pass `true` to update the message as the authenticated user; applicable to bot users as well. |
| `channel` | string | Yes | ID or name of the channel, private group, or IM channel containing the message to update. Can be specified as either 'channel' or 'channel_id'. Do NOT include the '#' prefix (e.g., use 'general' not '#general') - any leading '#' will be automatically stripped. |
| `file_ids` | array | No | Array of file IDs to attach to the updated message. Files must already be uploaded to Slack. |
| `metadata` | object | No | JSON object containing `event_type` (string) and `event_payload` (dict) fields for adding custom metadata to the message. |
| `fallback_text` | string | No | Optional only when using `blocks`. Maps to Slack's top-level `text` field for notifications, accessibility, search previews, and clients that cannot render blocks. This should be a short plain-text summary of the block content, not another visible message body. Omit it if you want Slack to infer fallback text from supported blocks. |
| `markdown_text` | string | No | Use this for normal LLM-written updated message content. Pass standard Markdown exactly as written; this tool sends it to Slack's native `markdown_text` argument without converting it to blocks. Do not use this together with `blocks`. Supports Slack's native markdown handling for headings, bold, italic, links, lists, code, quotes, dividers, tables, and task lists. Slack collapses literal empty Markdown lines; to force visible blank spacer rows, put a non-breaking space on each spacer line, e.g. `a\n\u00a0\n\u00a0\n\u00a0\nb`. For Slack mentions, use explicit entity syntax such as <@USER_ID>, <#CHANNEL_ID>, or <!subteam^GROUP_ID>; do not rely on @name or #name auto-linking. Use `blocks` instead when you need buttons, selects, checkboxes, image blocks, context rows, fields, accessories, or other interactive/layout controls. |
| `reply_broadcast` | boolean | No | If `true` and the message is a thread reply, broadcast the updated message to the channel. Defaults to `false`. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update Slack List

**Slug:** `SLACK_UPDATE_SLACK_LIST`

Updates a Slack List's metadata via `slackLists.update`. Only the List's `name`, `description_blocks`, and `todo_mode` are editable here. The List to update is identified by its `id` (not `list_id`). Descriptions are rich text — a plain string is wrapped into a `rich_text` block automatically. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | ID of the Slack List to update, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. NOTE: the parameter is named `id` (not `list_id`) for this method — pass the List ID here. |
| `name` | string | No | New name (title) for the List. Omit to leave the List name unchanged. |
| `todo_mode` | boolean | No | Whether the List is in to-do mode (rows behave like checkable tasks). Set true to enable to-do mode or false to disable it. Omit to leave it unchanged. |
| `description_blocks` | string | No | New description for the List. List descriptions are always rich text (Block Kit `rich_text`). For convenience you may supply a plain string and it will be wrapped into a `rich_text` block automatically; you may also pass an already-formed `rich_text` block dict or a list of blocks, which is sent through unchanged. Omit to leave the description unchanged. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update Slack List item

**Slug:** `SLACK_UPDATE_SLACK_LIST_ITEM`

Updates one or more cells in an EXISTING Slack List row via `slackLists.items.update`. Each cell is identified by `row_id` (an existing row ID matching `^Rec[A-Z0-9]{8,}$`) and `column_id` and carries a typed value; text columns require Block Kit `rich_text` (a plain string is wrapped automatically), and `select` takes the column's choice values (e.g. `["todo"]`). Use it to UPDATE existing rows; the live API rejects `row_id_to_create` inside a cell (despite Slack's inline example), so to ADD a row use `create_slack_list_item`. Requires a user token with the `lists:write` scope.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cells` | array | Yes | The cells to write. Each cell object identifies a single cell by its `row_id` and `column_id` and carries a typed value for that column. Text columns must use Block Kit `rich_text` (the plain `text` property is not accepted on input) — for convenience a cell may instead supply a plain string `text` and it will be wrapped into a `rich_text` block automatically. Other column types use their typed key, e.g. `select`, `user`, `date`, `number`, `checkbox`. For `select`, pass an array of the column's choice VALUES (e.g. `["todo"]`) — Slack does not mint separate per-option IDs.  UPDATE existing rows: each cell's `row_id` must be an EXISTING row ID matching `^Rec[A-Z0-9]{8,}$` (as returned by create_slack_list_item / list_slack_list_items). Do NOT try to create rows here: the live API rejects `row_id_to_create` inside a cell (`invalid additional property` at `/cells/N`), despite Slack's inline example showing it. To ADD a row, use `create_slack_list_item` (the reliable path). |
| `list_id` | string | Yes | ID of the Slack List that contains the row(s) to update, e.g. 'F0123456789'. This is the List file ID returned by create_slack_list. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update Slack user group

**Slug:** `SLACK_UPDATE_USER_GROUP`

Updates an existing Slack User Group, which must be specified by an existing `usergroup` ID, with new optional details such as its name, description, handle, or default channels.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | New name for the User Group. Must be unique among User Groups. |
| `handle` | string | No | New mention handle. Must be unique among channels, users, and User Groups. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `channels` | string | No | Comma-separated encoded channel IDs to set as default channels. |
| `usergroup` | string | Yes | Encoded ID of the existing User Group to update. |
| `description` | string | No | New short description for the User Group. |
| `include_count` | boolean | No | If true, include the number of users in the User Group in the response. |
| `enable_section` | boolean | No | Configure this user group to show as a sidebar section for all group members. Only relevant if group has 1 or more default channels added. |
| `additional_channels` | string | No | Comma-separated encoded channel IDs for which the User Group can custom add usergroup members to. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Update user group members

**Slug:** `SLACK_UPDATE_USER_GROUP_MEMBERS`

Replaces all members of an existing Slack User Group with a new list of valid user IDs.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `users` | string | Yes | Comma-separated string of encoded user IDs for the new, complete member list, replacing all existing members. User IDs typically start with 'U' or 'W'. |
| `team_id` | string | No | ID of the Slack workspace (team) to operate on, e.g. T0123456789. Use only with org-level Enterprise Grid tokens when you need to target a specific workspace; omit for single-workspace tokens. |
| `usergroup` | string | Yes | The encoded ID of the User Group whose members are to be updated. This ID typically starts with 'S'. |
| `include_count` | boolean | No | If true, the response `usergroup` object includes `user_count` and potentially `channel_count` fields, reflecting counts after the update. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |

### Upload or create a file in Slack

**Slug:** `SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK`

Upload files, images, screenshots, documents, or any media to Slack channels or threads. Supports all file types including images (PNG, JPG, JPEG, GIF), documents (PDF, DOCX, TXT), code files, and more. Can share files publicly in channels or as thread replies with optional comments. Large files may fail with `upload_too_large`; use SLACK_ADD_A_REMOTE_FILE_FROM_A_SERVICE for large uploads. If the API returns `ok=false` with `method_deprecated`, fall back to SLACK_ADD_A_REMOTE_FILE_FROM_A_SERVICE or SLACK_SEND_MESSAGE with a URL.

#### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | No | File(s) to upload. Accepts a single file or a list of files. At least one of 'content' or 'file' must be provided (but not both). The file name will be used in Slack. |
| `title` | string | No | Title of the file, displayed in Slack. |
| `token` | string | No | Authentication token; requires 'files:write' scope. |
| `content` | string | No | Text content of the file; use for text-based files. At least one of 'content' or 'file' must be provided (but not both). |
| `channels` | string | No | Channel ID where the file will be shared; if omitted, file is private to the uploader. Accepts the singular `channel` or plural `channels` for backward compatibility. Use channel ID (e.g., C1234567890) not channel name. Note: Due to API changes, only the first channel ID is used if multiple are provided. App must be a member of the target channel or the upload fails with `not_in_channel` or `channel_not_found`. |
| `filename` | string | No | Filename to be displayed in Slack. Required when using 'content' parameter. |
| `filetype` | string | No | Deprecated: File type detection is now automatic. This parameter is preserved for backward compatibility but no longer affects file uploads. |
| `thread_ts` | string | No | Timestamp of a parent message to upload this file as a reply; use the original message's 'ts' value (e.g., '1234567890.123456'). |
| `initial_comment` | string | No | Optional message to introduce the file in specified 'channels'. |

#### Output

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | string | Yes | Data from the action execution |
| `error` | string | No | Error if any occurred during the execution of the action |
| `successful` | boolean | Yes | Whether or not the action execution was successful or not |


## Triggers

### New Channel Created Trigger

**Slug:** `SLACK_CHANNEL_CREATED`

**Type:** webhook

Triggered when a new channel is created in Slack.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `created` | integer | Yes | The timestamp of when the channel was created, formatted as a Unix timestamp |
| `creator` | string | Yes | The ID of the user who created the channel |
| `id` | string | Yes | The ID of the channel |
| `name` | string | Yes | The name of the channel |

### Channel Message Received

**Slug:** `SLACK_CHANNEL_MESSAGE_RECEIVED`

**Type:** webhook

Triggered when a message is posted in a Slack channel
    (public, private, or multi-party IM). Does NOT match direct messages.

#### Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | string | No | Specific channel to watch. Null = all channels. |
| `channel_type` | string ("channel" | "group" | "mpim") | No | Filter by channel type. channel = public, group = private, mpim = multi-party IM. Null = all types. |
| `is_bot_message` | boolean | No | Filter by message source. true = only bot messages, false = only human messages, null = all. |
| `is_thread_reply` | boolean | No | Filter by thread status. true = only thread replies, false = only top-level, null = all. |

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `attachments` | array | No |  |
| `blocks` | array | No |  |
| `bot_id` | string | No |  |
| `channel` | string | Yes |  |
| `channel_type` | string | No |  |
| `files` | array | No |  |
| `subtype` | string | No |  |
| `team_id` | string | No |  |
| `text` | string | No |  |
| `thread_ts` | string | No |  |
| `ts` | string | Yes |  |
| `user` | string | No |  |

### Direct Message Received

**Slug:** `SLACK_DIRECT_MESSAGE_RECEIVED`

**Type:** webhook

Triggered when a new direct message (DM) is sent to a user in Slack.
    Catches all DMs across all DM channels.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `attachments` | array | No | Attachments included with the direct message, if any. Some Slack apps (like Datadog) send content via attachments rather than the top-level text field. |
| `bot_id` | string | Yes | The ID of the bot that sent the direct message |
| `channel` | string | Yes | The ID of the direct message channel |
| `channel_type` | string | Yes | The type of the channel (should be 'im' for direct messages) |
| `files` | array | No | Files uploaded with the direct message, if any. Present when subtype is 'file_share'. Contains file metadata including name, mimetype, and URLs. |
| `team_id` | string | Yes | The ID of the team where the direct message was sent |
| `text` | string | Yes | The text content of the direct message |
| `ts` | string | Yes | The timestamp of the direct message |
| `user` | string | Yes | The ID of the user who sent the direct message |

### Message Reaction Added

**Slug:** `SLACK_MESSAGE_REACTION_ADDED`

**Type:** webhook

Triggered when a reaction is added to a message in Slack.
    Supports optional filtering by channel and emoji name.

#### Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | string | No | Specific channel to watch. Null = all channels. |
| `emoji_name` | string | No | Filter by emoji short name (e.g. 'thumbsup', 'tada'). Null = all reactions. |

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_ts` | string | Yes | The timestamp of the reaction event |
| `message_channel` | string | Yes | The ID of the channel where the reacted-to message is located |
| `message_ts` | string | Yes | The timestamp of the message that was reacted to |
| `message_user` | string | No | The ID of the user who owns the message that was reacted to |
| `reaction` | string | Yes | The emoji short name of the reaction that was added |
| `team_id` | string | No | The ID of the team where the reaction occurred |
| `user` | string | Yes | The ID of the user who added the reaction |

### Message Reaction Removed

**Slug:** `SLACK_MESSAGE_REACTION_REMOVED`

**Type:** webhook

Triggered when a reaction is removed from a message in Slack.
    Supports optional filtering by channel and emoji name.

#### Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channel_id` | string | No | Specific channel to watch. Null = all channels. |
| `emoji_name` | string | No | Filter by emoji short name (e.g. 'thumbsup', 'tada'). Null = all reactions. |

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_ts` | string | Yes | The timestamp of the reaction event |
| `message_channel` | string | Yes | The ID of the channel where the reacted-to message is located |
| `message_ts` | string | Yes | The timestamp of the message that was reacted to |
| `message_user` | string | No | The ID of the user who owns the message that was reacted to |
| `reaction` | string | Yes | The emoji short name of the reaction that was removed |
| `team_id` | string | No | The ID of the team where the reaction occurred |
| `user` | string | Yes | The ID of the user who removed the reaction |

### Reaction Added Trigger

**Slug:** `SLACK_REACTION_ADDED`

**Type:** webhook

DEPRECATED: use `SLACK_MESSAGE_REACTION_ADDED` instead.

    Triggered when a reaction is added to a message in Slack.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_id` | string | Yes | The ID of the bot that posted the message |
| `channel_type` | string | Yes | The type of the channel where the message was posted |
| `event_ts` | string | Yes | The timestamp of the reaction event. Formatted as a Unix timestamp |
| `message_channel` | string | Yes | The ID of the channel where the message that was reacted to is located |
| `message_ts` | string | Yes | The timestamp of the message that was reacted to. Formatted as a Unix timestamp |
| `message_user` | string | No | The ID of the user who owns the message that was reacted to. Slack omits this for reactions on items posted without an owning user (e.g. file shares, system messages, or app-posted messages). |
| `reaction` | string | Yes | The type of reaction that was added |
| `team_id` | string | Yes | The ID of the team where the message was posted |
| `user` | string | Yes | The ID of the user who added the reaction |

### Reaction Removed Trigger

**Slug:** `SLACK_REACTION_REMOVED`

**Type:** webhook

DEPRECATED: use `SLACK_MESSAGE_REACTION_REMOVED` instead.

    Triggered when a reaction is removed from a message.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_id` | string | Yes | The ID of the bot that posted the message |
| `channel_type` | string | Yes | The type of the channel where the message was posted |
| `event_ts` | string | Yes | The timestamp of the reaction event. Formatted as a Unix timestamp |
| `message_channel` | string | Yes | The ID of the channel where the message that was reacted to is located |
| `message_ts` | string | Yes | The timestamp of the message that was reacted to. Formatted as a Unix timestamp |
| `message_user` | string | No | The ID of the user who owns the message that was reacted to. Slack omits this for reactions on items posted without an owning user (e.g. file shares, system messages, or app-posted messages). |
| `reaction` | string | Yes | The type of reaction that was added |
| `team_id` | string | Yes | The ID of the team where the message was posted |
| `user` | string | Yes | The ID of the user who added the reaction |

### New Bot Message Received Trigger

**Slug:** `SLACK_RECEIVE_BOT_MESSAGE`

**Type:** webhook

DEPRECATED: use `SLACK_CHANNEL_MESSAGE_RECEIVED` with
    `is_bot_message=true` instead.

    Triggered when a new bot message is posted to a Slack channel.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `attachments` | array | No | Attachments included with the bot message, if any. Slack apps (like Datadog) often send their content via attachments rather than the top-level text field. |
| `bot_id` | string | No | The ID of the bot that posted the message |
| `channel` | string | Yes | The ID of the channel where the bot message was posted |
| `channel_type` | string | No | The type of the channel where the bot message was posted |
| `files` | array | No | Files uploaded with the bot message, if any. Present when subtype is 'file_share'. Contains file metadata including name, mimetype, and URLs. |
| `subtype` | string | Yes | The subtype of the message (should be 'bot_message') |
| `team_id` | string | No | The ID of the team where the bot message was posted |
| `text` | string | Yes | The text content of the bot message |
| `ts` | string | Yes | The timestamp of the bot message |
| `username` | string | No | The username of the bot that posted the message |

### New Message Received Trigger

**Slug:** `SLACK_RECEIVE_MESSAGE`

**Type:** webhook

DEPRECATED: use `SLACK_CHANNEL_MESSAGE_RECEIVED` instead.

    Triggered when a new message is posted to a Slack channel.

#### Payload

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `attachments` | array | No | Attachments included with the message, if any. Some Slack apps (like Datadog) send content via attachments rather than the top-level text field. |
| `bot_id` | string | No | The ID of the bot that posted the message |
| `channel` | string | Yes | The ID of the channel where the message was posted |
| `channel_type` | string | No | The type of the channel where the message was posted |
| `files` | array | No | Files uploaded with the message, if any. Present when subtype is 'file_share'. Contains file metadata including name, mimetype, and URLs. |
| `team_id` | string | No | The ID of the team where the message was posted |
| `text` | string | Yes | The text content of the message |
| `ts` | string | Yes | The timestamp of the message |
| `user` | string | No | The ID of the user who posted the message |
