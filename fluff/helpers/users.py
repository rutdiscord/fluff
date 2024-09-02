# Commonly used username_system function

def username_system(self, user):
        return (
            "**"
            + self.bot.pacify_name(user.global_name)
            + f"** [{self.bot.pacify_name(str(user))}]"
            if user.global_name
            else f"**{self.bot.pacify_name(str(user))}**"
        )