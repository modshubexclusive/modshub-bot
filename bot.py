import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

TOKEN = os.environ.get("TOKEN")
PRODUCTS_FILE = "products.txt"
REPORTS_DIR = "reports"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- SIMPLE WEB SERVER FOR RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ------------------------------------

def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return ["General Bug / Issue"]
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = [line.strip() for line in f if line.strip()]
    return products if products else ["General Bug / Issue"]

class BugReportModal(discord.ui.Modal):
    def __init__(self, product_name: str):
        # ΤΟ ΔΙΟΡΘΩΣΑΜΕ ΕΔΩ: Ο τίτλος περιορίζεται αυστηρά κάτω από 45 χαρακτήρες
        super().__init__(title=f"Report: {product_name[:30]}")
        self.product_name = product_name

        self.issue_type = discord.ui.TextInput(
            label="Issue Type",
            placeholder="Bug / Error or Suggestion / Request?",
            required=True
        )
        self.description = discord.ui.TextInput(
            label="Description",
            placeholder="Describe the issue in detail...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.add_item(self.issue_type)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        safe_name = "".join(c if c.isalnum() else "_" for c in self.product_name)
        file_path = os.path.join(REPORTS_DIR, f"{safe_name}.md")

        report_content = (
            f"# Product: {self.product_name}\n"
            f"**User:** {interaction.user} (ID: {interaction.user.id})\n"
            f"**Type:** {self.issue_type.value}\n"
            f"**Description:**\n{self.description.value}\n\n"
            "---\n"
        )

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(report_content)

        await interaction.response.send_message(
            "✅ Your report has been successfully recorded! Thank you.", ephemeral=True
        )

class ProductSelectView(discord.ui.View):
    def __init__(self, products, current_page=0):
        super().__init__(timeout=None)
        self.products = products
        self.current_page = current_page
        self.max_pages = max(0, (len(products) - 1) // 25)
        
        self.setup_components()

    def setup_components(self):
        self.clear_items()
        
        start = self.current_page * 25
        end = start + 25
        page_products = self.products[start:end]

        options = [discord.SelectOption(label=p[:100], value=p[:100]) for p in page_products]
        
        select = discord.ui.Select(
            placeholder=f"Select product (Page {self.current_page + 1}/{self.max_pages + 1})...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"product_select_{self.current_page}"
        )
        select.callback = self.select_callback
        self.add_item(select)

        if self.max_pages > 0:
            prev_button = discord.ui.Button(
                label="⬅️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page == 0),
                custom_id="prev_page"
            )
            prev_button.callback = self.prev_callback
            self.add_item(prev_button)

            next_button = discord.ui.Button(
                label="Next ➡️",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page == self.max_pages),
                custom_id="next_page"
            )
            next_button.callback = self.next_callback
            self.add_item(next_button)

    async def select_callback(self, interaction: discord.Interaction):
        modal = BugReportModal(interaction.data["values"][0])
        await interaction.response.send_modal(modal)

    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            self.setup_components()
            await interaction.message.edit(view=self)

    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.setup_components()
            await interaction.message.edit(view=self)

@bot.command(name="setup_menu")
@commands.has_permissions(administrator=True)
async def setup_menu(ctx):
    await ctx.message.delete()
    products = load_products()
    view = ProductSelectView(products)
    await ctx.send("📋 **Bug & Request Reporting System**\nSelect your product from the list below:", view=view)

@bot.command(name="get_reports")
@commands.has_permissions(administrator=True)
async def get_reports(ctx):
    if not os.path.exists(REPORTS_DIR) or not os.listdir(REPORTS_DIR):
        await ctx.send("📂 No saved reports yet.", delete_after=10)
        return
    
    await ctx.send("📂 Here are the report files:")
    for file_name in os.listdir(REPORTS_DIR):
        file_path = os.path.join(REPORTS_DIR, file_name)
        if os.path.isfile(file_path):
            await ctx.send(file=discord.File(file_path))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

bot.run(TOKEN)
