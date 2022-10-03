import asyncio
import discord


async def send_message_with_buttons(self, ctx, content):
    pages = len(content)
    cur_page = 1
    message = await ctx.send(f"```\n{content[cur_page-1]}\nPág {cur_page} de {pages}\n```")
    if(pages > 1):
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=180)
                if(not user.bot):
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "▶️" and cur_page != pages:
                        cur_page += 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        await message.remove_reaction(reaction, user)

                    elif str(reaction.emoji) == "◀️" and cur_page > 1:
                        cur_page -= 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        await message.remove_reaction(reaction, user)

                    else:
                        await message.remove_reaction(reaction, user)
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
            except asyncio.TimeoutError:
                break
                # ending the loop if user doesn't react after x seconds