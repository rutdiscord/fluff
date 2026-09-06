import discord

STAR_EMOJI = "⭐"
async def build_message_embed(message: discord.Message) -> list[discord.Embed]:
    """Build a list of embeds for a message."""
    description_parts = []

    ref = message.reference
    reply_description: str | None = None
    if ref is not None:
        resolved = ref.resolved
        if resolved is None and ref.message_id is not None:
            try:
                resolved = await message.channel.fetch_message(ref.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                resolved = None

        if isinstance(resolved, discord.Message):
            reply_description = f"> ↪ **[{resolved.author.display_name}]({resolved.jump_url})** - {resolved.content if resolved.content else "*[no content]*"}"
        else:
            description_parts.append("> ↪ *original message unavailable*")

    if message.content:
        description_parts.append(message.content)

    if reply_description:
        description_parts.append(reply_description)

    primary = discord.Embed(
        description="\n\n".join(description_parts) if description_parts else None,
        color=discord.Color.gold(),
        url=message.jump_url,
    )
    primary.set_author(
        name=f"{message.author.display_name} • #{message.channel.name}",
        url=message.jump_url,
        icon_url=message.author.display_avatar.url,
    )

    image_urls = [
        a.url for a in message.attachments
        if a.content_type and a.content_type.startswith("image/")
    ]
    if not image_urls:
        for e in message.embeds:
            if e.image and e.image.url:
                image_urls.append(e.image.url)
            elif e.thumbnail and e.thumbnail.url:
                image_urls.append(e.thumbnail.url)

    embeds = [primary]

    star_count = 0
    for reaction in message.reactions:
        if str(reaction.emoji) == STAR_EMOJI:
            star_count = reaction.count
            break

    primary.set_footer(text=f"{STAR_EMOJI} {star_count}")

    if image_urls:
        for image_url in image_urls:
            gallery_embed = discord.Embed(color=discord.Color.gold(), url=message.jump_url)
            gallery_embed.set_image(url=image_url)
            embeds.append(gallery_embed)

    primary.timestamp = message.created_at

    return embeds