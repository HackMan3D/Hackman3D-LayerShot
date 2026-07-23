using System.Diagnostics;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Win32;

namespace Hackman3D.LayerShot.Windows;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}

internal sealed record PrinterProfile(string Name, string Model, string Host, int Port);
internal sealed record AppSettings(List<PrinterProfile> Printers, string EspHost = "hackman-layershot.local");

internal sealed class MainForm : Form
{
    private readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(5) };
    private readonly FlowLayoutPanel dashboard = new() { Dock = DockStyle.Fill, AutoScroll = true, Padding = new Padding(14) };
    private readonly ComboBox models = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 260 };
    private readonly TextBox printerName = new() { Width = 260, PlaceholderText = "Ex. K2 Atelier" };
    private readonly TextBox printerHost = new() { Width = 260, PlaceholderText = "192.168.1.42" };
    private readonly NumericUpDown printerPort = new() { Width = 100, Minimum = 1, Maximum = 65535, Value = 4408 };
    private readonly TextBox espHost = new() { Width = 260, Text = "hackman-layershot.local" };
    private readonly ComboBox wifiNetworks = new() { Width = 260, DropDownStyle = ComboBoxStyle.DropDown };
    private readonly TextBox wifiPassword = new() { Width = 260, UseSystemPasswordChar = true };
    private readonly ComboBox autonomousPrinter = new() { Width = 260, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly NumericUpDown every = new() { Minimum = 1, Maximum = 999, Value = 1 };
    private readonly NumericUpDown skip = new() { Minimum = 0, Maximum = 9999 };
    private readonly NumericUpDown stop = new() { Minimum = 0, Maximum = 99999 };
    private readonly NumericUpDown delay = new() { Minimum = 0, Maximum = 30, DecimalPlaces = 1, Increment = .1M, Value = 1 };
    private readonly ComboBox serialPorts = new() { Width = 260, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly Label status = new() { AutoSize = false, Width = 110, Height = 32, ForeColor = Color.FromArgb(170, 180, 193), TextAlign = ContentAlignment.MiddleRight, Text = "READY" };
    private readonly Dictionary<string, Control> cards = [];
    private readonly Dictionary<string, Panel> pages = [];
    private readonly Dictionary<string, Button> navButtons = [];
    private readonly Panel contentHost = new() { Dock = DockStyle.Fill, BackColor = Color.FromArgb(13, 15, 19), Padding = new Padding(34, 28, 34, 28) };
    private AppSettings settings = new([]);
    private readonly string settingsPath;
    private readonly System.Windows.Forms.Timer pollTimer = new() { Interval = 2000 };

    public MainForm()
    {
        Text = "Hackman3D LayerShot";
        MinimumSize = new Size(1080, 720);
        Size = new Size(1360, 860);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(13, 15, 19);
        ForeColor = Color.FromArgb(240, 243, 247);
        Font = new Font("Segoe UI", 10, FontStyle.Regular);
        AutoScaleMode = AutoScaleMode.Dpi;
        KeyPreview = true;
        settingsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Hackman3D", "LayerShot", "settings.json");

        models.Items.AddRange(["K2 / K2 Plus", "K1 / K1C / K1 Max", "SPARKX i7 / i7 Color Combo", "Ender-3 V3 / KE", "CR-10 SE", "Klipper / Moonraker"]);
        models.SelectedIndex = 0;
        foreach (var input in new Control[] { models, printerName, printerHost, printerPort, espHost, wifiNetworks, wifiPassword, autonomousPrinter, every, skip, stop, delay, serialPorts })
            StyleInput(input);

        var shell = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 2, BackColor = BackColor };
        shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 224));
        shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 78));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        shell.Controls.Add(MakeBrand(), 0, 0);
        shell.Controls.Add(MakeHeader(), 1, 0);
        shell.Controls.Add(MakeSidebar(), 0, 1);
        shell.Controls.Add(contentHost, 1, 1);
        Controls.Add(shell);

        RegisterPage("dashboard", MakeDashboardPage());
        RegisterPage("setup", MakeSetupPage());
        RegisterPage("timelapse", MakeTimelapsePage());
        RegisterPage("about", MakeAboutPage());
        ShowPage("dashboard");

        LoadSettings();
        RefreshDashboard();
        pollTimer.Tick += async (_, _) => await PollAllAsync();
        pollTimer.Start();
        Shown += async (_, _) => await PollAllAsync();
        KeyDown += (_, e) => { if (e.Control && e.KeyCode == Keys.Q) Close(); };
    }

    private Control MakeBrand()
    {
        var brand = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(9, 11, 14), Padding = new Padding(22, 15, 10, 10) };
        var mark = new Label { Text = "H3D", AutoSize = false, Width = 44, Height = 44, BackColor = Color.FromArgb(25, 135, 255), ForeColor = Color.White, Font = new Font("Segoe UI", 9.5f, FontStyle.Bold), TextAlign = ContentAlignment.MiddleCenter };
        var name = new Label { Text = "LayerShot", Left = 54, Top = 9, Width = 138, Height = 27, ForeColor = Color.White, Font = new Font("Segoe UI", 12.5f, FontStyle.Bold) };
        var version = new Label { Text = "HACKMAN3D  •  0.4.1", Left = 55, Top = 38, Width = 137, Height = 18, ForeColor = Color.FromArgb(104, 118, 136), Font = new Font("Segoe UI", 6.5f, FontStyle.Bold) };
        brand.Controls.Add(mark); brand.Controls.Add(name); brand.Controls.Add(version);
        return brand;
    }

    private Control MakeHeader()
    {
        var header = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(17, 20, 25), Padding = new Padding(28, 16, 22, 14) };
        var left = new Label { Text = "AUTONOMOUS 3D PRINT TIMELAPSE", Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, ForeColor = Color.FromArgb(142, 155, 171), Font = new Font("Segoe UI", 7.5f, FontStyle.Bold) };
        var links = new FlowLayoutPanel { Dock = DockStyle.Right, Width = 342, FlowDirection = FlowDirection.RightToLeft, WrapContents = false, Padding = new Padding(0, 5, 0, 0) };
        links.Controls.Add(HeaderButton("DONATE", "https://paypal.me/Hackman3D", true));
        links.Controls.Add(HeaderButton("FEEDBACK", "mailto:hackman3d.pro@gmail.com"));
        links.Controls.Add(HeaderButton("YOUTUBE", "https://www.youtube.com/@hackman3D"));
        links.Controls.Add(HeaderButton("INSTAGRAM", "https://www.instagram.com/hackman_3dprint/"));
        header.Controls.Add(left); header.Controls.Add(links); header.Controls.Add(status); status.Dock = DockStyle.Right;
        return header;
    }

    private Control MakeSidebar()
    {
        var side = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(9, 11, 14), Padding = new Padding(14, 22, 14, 18) };
        var nav = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 280, FlowDirection = FlowDirection.TopDown, WrapContents = false };
        nav.Controls.Add(Nav("dashboard", "▦", "PRINTERS"));
        nav.Controls.Add(Nav("setup", "⚙", "INSTALLATION"));
        nav.Controls.Add(Nav("timelapse", "▶", "TIMELAPSE"));
        nav.Controls.Add(Nav("about", "♥", "HACKMAN3D"));
        var footer = new Label { Dock = DockStyle.Bottom, Height = 64, Text = "CREATED, DESIGNED\n& CODED BY HACKMAN3D", ForeColor = Color.FromArgb(78, 91, 108), Font = new Font("Segoe UI", 7.5f, FontStyle.Bold), TextAlign = ContentAlignment.BottomLeft };
        side.Controls.Add(nav); side.Controls.Add(footer);
        return side;
    }

    private Panel MakeDashboardPage()
    {
        var page = Page("PRINTERS", "Monitor every Creality or Moonraker printer independently.");
        dashboard.Padding = new Padding(0, 18, 0, 0);
        dashboard.BackColor = Color.FromArgb(13, 15, 19);
        page.Controls.Add(dashboard);
        return page;
    }

    private Panel MakeSetupPage()
    {
        var page = Page("INSTALLATION", "Configure the printer, ESP32-C3, Wi-Fi and iPhone in one place.");
        var flow = Stack();
        flow.Controls.Add(StepStrip());
        flow.Controls.Add(Group("01", "ADD A PRINTER",
            Field("Display name", printerName), Field("Printer family", models), Field("Network address", printerHost), Field("Moonraker port", printerPort),
            Button("TEST && SAVE PRINTER", async (_, _) => await Safe(AddPrinterAsync))));
        flow.Controls.Add(Group("02", "INSTALL ESP32-C3 FIRMWARE",
            Hint("Connect the ESP32-C3 with a USB data cable. The application includes the firmware and flashing tool."),
            Field("USB serial port", serialPorts), Button("DETECT ESP32", (_, _) => ScanSerialPorts(), false),
            Button("INSTALL / UPDATE FIRMWARE", async (_, _) => await Safe(FlashEspAsync))));
        flow.Controls.Add(Group("03", "WI-FI & IPHONE PAIRING",
            Field("ESP32 network address", espHost), Field("Wi-Fi network", wifiNetworks), Field("Wi-Fi password", wifiPassword),
            Button("SCAN WI-FI", (_, _) => ScanWifi(), false),
            Button("USE SAVED WINDOWS PASSWORD", (_, _) => ReadWifiPassword(), false),
            Button("SEND WI-FI TO ESP32", async (_, _) => await Safe(ConfigureWifiAsync)),
            Button("TEST ESP32", async (_, _) => await Safe(TestEspAsync), false),
            Button("START IPHONE PAIRING", async (_, _) => await Safe(() => PostEspAsync("/pair"))),
            Button("FORGET PAIRED IPHONE", async (_, _) => await Safe(() => PostEspAsync("/reset-bonds")), false)));
        flow.Controls.Add(Group("04", "AUTONOMOUS CAPTURE",
            Hint("These settings are stored inside the ESP32. The PC can remain switched off during the print."),
            Field("Monitored printer", autonomousPrinter), Field("Capture every N layers", every),
            Field("Skip first layers", skip), Field("Stop after layer (0 = never)", stop),
            Field("Stabilization delay (seconds)", delay),
            Button("SAVE SETTINGS TO ESP32", async (_, _) => await Safe(ConfigureAutonomousAsync))));
        page.Controls.Add(flow);
        return page;
    }

    private Panel MakeTimelapsePage()
    {
        var page = Page("TIMELAPSE", "Import your layer photos and export a ready-to-share MP4.");
        var flow = Stack();
        var selected = Hint("No photos selected");
        var fps = new NumericUpDown { Minimum = 12, Maximum = 60, Value = 30 };
        StyleInput(fps);
        var images = new List<string>();
        var drop = Group("01", "IMPORT PHOTOS",
            selected,
            Button("SELECT PHOTOS…", (_, _) => {
                using var dialog = new OpenFileDialog { Multiselect = true, Filter = "Images|*.jpg;*.jpeg;*.png;*.webp" };
                if (dialog.ShowDialog() == DialogResult.OK) { images = dialog.FileNames.Order().ToList(); selected.Text = $"{images.Count} PHOTOS SELECTED"; }
            }),
            Field("Frames per second", fps),
            Button("CREATE MP4…", async (_, _) => await Safe(() => ExportTimelapseAsync(images, (int)fps.Value))));
        flow.Controls.Add(drop);
        page.Controls.Add(flow);
        return page;
    }

    private Panel MakeAboutPage()
    {
        var page = Page("HACKMAN3D", "Free software, built for the 3D-printing community.");
        var flow = Stack();
        flow.Controls.Add(Group("♥", "SUPPORT LAYERSHOT",
            Hint("Hackman3D LayerShot is developed and shared free of charge. Donations, feedback and social follows help keep the project moving."),
            Link("CREALITY CLOUD", "https://www.crealitycloud.com/user/5221417142"),
            Link("TIKTOK", "https://www.tiktok.com/@hackman3d"),
            Link("INSTAGRAM", "https://www.instagram.com/hackman_3dprint/"),
            Link("YOUTUBE", "https://www.youtube.com/@hackman3D"),
            Link("EMAIL / FEEDBACK", "mailto:hackman3d.pro@gmail.com"),
            Button("SUPPORT WITH PAYPAL", (_, _) => Open("https://paypal.me/Hackman3D"))));
        page.Controls.Add(flow);
        return page;
    }

    private static Panel Page(string title, string subtitle)
    {
        var page = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(13, 15, 19) };
        var heading = new Panel { Dock = DockStyle.Top, Height = 86 };
        heading.Controls.Add(new Label { Text = title, Dock = DockStyle.Top, Height = 48, ForeColor = Color.White, Font = new Font("Segoe UI", 27, FontStyle.Bold) });
        heading.Controls.Add(new Label { Text = subtitle, Dock = DockStyle.Bottom, Height = 30, ForeColor = Color.FromArgb(128, 141, 159), Font = new Font("Segoe UI", 10) });
        page.Controls.Add(heading);
        return page;
    }
    private static FlowLayoutPanel Stack() => new() { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, Padding = new Padding(0, 18, 14, 24), BackColor = Color.FromArgb(13, 15, 19) };
    private static FlowLayoutPanel Group(string number, string title, params Control[] controls)
    {
        var group = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoSize = true, Width = 900, Padding = new Padding(24), Margin = new Padding(0, 0, 0, 18), BackColor = Color.FromArgb(24, 28, 34) };
        var top = new FlowLayoutPanel { Width = 840, Height = 42, WrapContents = false };
        top.Controls.Add(new Label { Text = number, Width = 42, Height = 30, BackColor = Color.FromArgb(25, 135, 255), ForeColor = Color.White, TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Segoe UI", 9, FontStyle.Bold), Margin = new Padding(0, 0, 14, 0) });
        top.Controls.Add(new Label { Text = title, Width = 680, Height = 30, ForeColor = Color.White, Font = new Font("Segoe UI", 15, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft });
        group.Controls.Add(top); group.Controls.AddRange(controls);
        return group;
    }
    private static FlowLayoutPanel Field(string label, Control input)
    {
        var row = new FlowLayoutPanel { FlowDirection = FlowDirection.LeftToRight, Width = 840, Height = 48, WrapContents = false, Margin = new Padding(0, 2, 0, 2) };
        row.Controls.Add(new Label { Text = label, Width = 330, Height = 38, ForeColor = Color.FromArgb(179, 189, 202), TextAlign = ContentAlignment.MiddleLeft });
        row.Controls.Add(input);
        return row;
    }
    private static Button Button(string text, EventHandler action, bool primary = true)
    {
        var button = new Button { Text = text, AutoSize = true, MinimumSize = new Size(190, 40), Height = 40, BackColor = primary ? Color.FromArgb(25, 135, 255) : Color.FromArgb(38, 45, 55), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 8.5f, FontStyle.Bold), Cursor = Cursors.Hand, Margin = new Padding(0, 8, 10, 2) };
        button.FlatAppearance.BorderSize = primary ? 0 : 1; button.FlatAppearance.BorderColor = Color.FromArgb(63, 73, 87);
        button.Click += action;
        return button;
    }
    private static LinkLabel Link(string text, string url)
    {
        var link = new LinkLabel { Text = "↗  " + text, AutoSize = true, LinkColor = Color.FromArgb(93, 178, 255), ActiveLinkColor = Color.White, Font = new Font("Segoe UI", 10, FontStyle.Bold), Margin = new Padding(0, 8, 0, 6) };
        link.Click += (_, _) => Open(url);
        return link;
    }
    private static Label Hint(string text) => new() { Text = text, AutoSize = true, MaximumSize = new Size(820, 0), ForeColor = Color.FromArgb(137, 150, 167), Font = new Font("Segoe UI", 9.5f), Margin = new Padding(0, 4, 0, 10) };
    private static void StyleInput(Control input)
    {
        input.Width = input is NumericUpDown ? 180 : 400;
        input.Height = 38;
        input.BackColor = Color.FromArgb(13, 16, 21);
        input.ForeColor = Color.FromArgb(235, 239, 244);
        input.Font = new Font("Segoe UI", 10);
        input.Margin = new Padding(0, 4, 0, 0);
        if (input is ComboBox combo) combo.FlatStyle = FlatStyle.Flat;
        if (input is NumericUpDown numeric) numeric.BorderStyle = BorderStyle.FixedSingle;
        if (input is TextBox text) text.BorderStyle = BorderStyle.FixedSingle;
    }
    private static void Open(string url) => Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    private async Task Safe(Func<Task> action)
    {
        try { await action(); }
        catch (Exception ex) { SetStatus("ERROR  •  " + ex.Message); }
    }
    private Button HeaderButton(string text, string url, bool accent = false)
    {
        var button = new Button { Text = text, Width = accent ? 76 : 78, Height = 34, FlatStyle = FlatStyle.Flat, BackColor = accent ? Color.FromArgb(25, 135, 255) : Color.FromArgb(17, 20, 25), ForeColor = accent ? Color.White : Color.FromArgb(151, 164, 181), Font = new Font("Segoe UI", 7, FontStyle.Bold), Cursor = Cursors.Hand, Margin = new Padding(5, 0, 0, 0) };
        button.FlatAppearance.BorderSize = accent ? 0 : 1; button.FlatAppearance.BorderColor = Color.FromArgb(44, 51, 61);
        button.Click += (_, _) => Open(url);
        return button;
    }
    private Button Nav(string key, string icon, string text)
    {
        var button = new Button { Text = $"  {icon}    {text}", Width = 194, Height = 48, FlatStyle = FlatStyle.Flat, TextAlign = ContentAlignment.MiddleLeft, BackColor = Color.FromArgb(9, 11, 14), ForeColor = Color.FromArgb(132, 145, 162), Font = new Font("Segoe UI", 8.5f, FontStyle.Bold), Cursor = Cursors.Hand, Margin = new Padding(0, 0, 0, 6) };
        button.FlatAppearance.BorderSize = 0; button.Click += (_, _) => ShowPage(key); navButtons[key] = button;
        return button;
    }
    private static Control StepStrip()
    {
        var strip = new FlowLayoutPanel { Width = 900, Height = 48, WrapContents = false, Margin = new Padding(0, 0, 0, 18), BackColor = Color.FromArgb(18, 21, 27), Padding = new Padding(14, 9, 8, 8) };
        foreach (var step in new[] { "1  PRINTER", "2  ESP32 USB", "3  WI-FI", "4  IPHONE" })
            strip.Controls.Add(new Label { Text = step, Width = 202, Height = 28, ForeColor = Color.FromArgb(139, 154, 173), Font = new Font("Segoe UI", 8, FontStyle.Bold), TextAlign = ContentAlignment.MiddleCenter });
        return strip;
    }
    private void RegisterPage(string key, Panel page)
    {
        pages[key] = page;
        contentHost.Controls.Add(page);
    }
    private void ShowPage(string key)
    {
        foreach (var item in pages) item.Value.Visible = item.Key == key;
        foreach (var item in navButtons)
        {
            var active = item.Key == key;
            item.Value.BackColor = active ? Color.FromArgb(25, 45, 68) : Color.FromArgb(9, 11, 14);
            item.Value.ForeColor = active ? Color.FromArgb(91, 181, 255) : Color.FromArgb(132, 145, 162);
        }
        if (pages.TryGetValue(key, out var page)) page.BringToFront();
    }

    private async Task AddPrinterAsync()
    {
        var host = printerHost.Text.Trim().Replace("http://", "").Replace("https://", "").Trim('/');
        if (string.IsNullOrWhiteSpace(host)) { SetStatus("Saisissez l’adresse IP."); return; }
        var profile = new PrinterProfile(string.IsNullOrWhiteSpace(printerName.Text) ? models.Text : printerName.Text.Trim(), models.Text, host, (int)printerPort.Value);
        try
        {
            await ReadPrinterAsync(profile);
            settings.Printers.RemoveAll(p => p.Host == profile.Host && p.Port == profile.Port);
            settings.Printers.Add(profile);
            SaveSettings();
            RefreshDashboard();
            SetStatus($"{profile.Name} connectée et enregistrée.");
        }
        catch (Exception ex) { SetStatus($"Connexion impossible : {ex.Message}"); }
    }

    private async Task<JsonElement> ReadPrinterAsync(PrinterProfile profile)
    {
        var url = $"http://{profile.Host}:{profile.Port}/printer/objects/query?print_stats&virtual_sdcard&display_status";
        using var response = await http.GetAsync(url);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<JsonElement>();
    }

    private void RefreshDashboard()
    {
        dashboard.Controls.Clear();
        cards.Clear();
        autonomousPrinter.Items.Clear();
        foreach (var profile in settings.Printers)
        {
            autonomousPrinter.Items.Add(profile);
            var box = new Panel { Width = 490, Height = 244, BackColor = Color.FromArgb(24, 28, 34), Padding = new Padding(22), Margin = new Padding(0, 0, 18, 18) };
            var dot = new Label { Text = "●", Left = 22, Top = 22, Width = 22, Height = 24, ForeColor = Color.FromArgb(255, 159, 10), Font = new Font("Segoe UI", 12) };
            var title = new Label { Text = profile.Name, Left = 48, Top = 18, Width = 320, Height = 28, ForeColor = Color.White, Font = new Font("Segoe UI", 15, FontStyle.Bold) };
            var identity = new Label { Text = $"{profile.Model}  •  {profile.Host}:{profile.Port}", Left = 49, Top = 48, Width = 400, Height = 22, ForeColor = Color.FromArgb(117, 132, 151), Font = new Font("Segoe UI", 8.5f) };
            var separator = new Panel { Left = 22, Top = 82, Width = 446, Height = 1, BackColor = Color.FromArgb(48, 56, 67) };
            var content = new Label { Left = 22, Top = 96, Width = 446, Height = 88, Font = new Font("Segoe UI", 10), ForeColor = Color.FromArgb(202, 211, 222), Text = "CONNECTING TO MOONRAKER…" };
            var remove = Button("REMOVE", (_, _) => { }, false); remove.Width = 105; remove.Height = 34; remove.Left = 22; remove.Top = 194;
            remove.Click += (_, _) => { settings.Printers.Remove(profile); SaveSettings(); RefreshDashboard(); };
            var camera = Button("OPEN CAMERA", (_, _) => { }); camera.Width = 140; camera.Height = 34; camera.Left = 328; camera.Top = 194;
            camera.Click += async (_, _) => await OpenCameraAsync(profile);
            box.Controls.Add(dot); box.Controls.Add(title); box.Controls.Add(identity); box.Controls.Add(separator); box.Controls.Add(content); box.Controls.Add(camera); box.Controls.Add(remove);
            dashboard.Controls.Add(box);
            cards[$"{profile.Host}:{profile.Port}"] = content;
        }
        if (settings.Printers.Count == 0)
        {
            var empty = new Panel { Width = 700, Height = 220, BackColor = Color.FromArgb(24, 28, 34) };
            empty.Controls.Add(new Label { Text = "NO PRINTERS YET", Left = 28, Top = 22, Width = 620, Height = 40, ForeColor = Color.White, Font = new Font("Segoe UI", 17, FontStyle.Bold) });
            empty.Controls.Add(new Label { Text = "Open Installation to connect your first Creality or Moonraker printer.", Left = 28, Top = 68, Width = 630, Height = 32, ForeColor = Color.FromArgb(135, 149, 167) });
            var add = Button("OPEN INSTALLATION", (_, _) => ShowPage("setup")); add.Dock = DockStyle.Bottom; add.Width = 190;
            empty.Controls.Add(add); dashboard.Controls.Add(empty);
        }
        if (autonomousPrinter.Items.Count > 0) autonomousPrinter.SelectedIndex = 0;
    }

    private async Task PollAllAsync()
    {
        foreach (var profile in settings.Printers.ToArray())
        {
            if (!cards.TryGetValue($"{profile.Host}:{profile.Port}", out var control) || control is not Label label) continue;
            try
            {
                var root = await ReadPrinterAsync(profile);
                var data = root.GetProperty("result").GetProperty("status");
                var stats = data.GetProperty("print_stats");
                var sd = data.GetProperty("virtual_sdcard");
                var state = stats.GetProperty("state").GetString() ?? "—";
                var file = stats.GetProperty("filename").GetString() ?? "";
                var layer = sd.TryGetProperty("layer", out var l) ? l.GetInt32() : 0;
                var total = sd.TryGetProperty("layer_count", out var t) ? t.GetInt32() : 0;
                var progress = sd.TryGetProperty("progress", out var p) ? p.GetDouble() : 0;
                label.Text = $"STATUS     {state.ToUpperInvariant()}\nLAYER       {layer} / {total}       •       PROGRESS     {progress:P0}\n{file}";
            }
            catch { label.Text = "OFFLINE\nCheck the printer address and local network connection."; }
        }
    }

    private async Task OpenCameraAsync(PrinterProfile profile)
    {
        try
        {
            var webcams = await http.GetFromJsonAsync<JsonElement>($"http://{profile.Host}:{profile.Port}/server/webcams/list");
            var list = webcams.GetProperty("result").GetProperty("webcams");
            if (list.GetArrayLength() == 0) { SetStatus("Cette imprimante ne publie pas sa caméra sur Moonraker."); return; }
            var stream = list[0].GetProperty("stream_url").GetString() ?? "";
            var url = stream.StartsWith("http") ? stream : $"http://{profile.Host}:{profile.Port}/{stream.TrimStart('/')}";
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception ex) { SetStatus($"Caméra indisponible : {ex.Message}"); }
    }

    private void ScanWifi()
    {
        wifiNetworks.Items.Clear();
        var output = Run("netsh", "wlan show networks mode=bssid");
        foreach (var line in output.Split('\n'))
        {
            var trimmed = line.Trim();
            if (!trimmed.StartsWith("SSID ", StringComparison.OrdinalIgnoreCase) || !trimmed.Contains(':')) continue;
            var value = trimmed[(trimmed.IndexOf(':') + 1)..].Trim();
            if (!string.IsNullOrEmpty(value) && !wifiNetworks.Items.Contains(value)) wifiNetworks.Items.Add(value);
        }
        if (wifiNetworks.Items.Count > 0) wifiNetworks.SelectedIndex = 0;
        SetStatus($"{wifiNetworks.Items.Count} réseau(x) trouvé(s).");
    }

    private void ReadWifiPassword()
    {
        var ssid = wifiNetworks.Text.Trim();
        if (ssid.Length == 0) return;
        var output = Run("netsh", $"wlan show profile name=\"{ssid}\" key=clear");
        var line = output.Split('\n').FirstOrDefault(x => x.Contains("Key Content", StringComparison.OrdinalIgnoreCase) || x.Contains("Contenu de la clé", StringComparison.OrdinalIgnoreCase));
        if (line?.Contains(':') == true) { wifiPassword.Text = line[(line.IndexOf(':') + 1)..].Trim(); SetStatus("Mot de passe récupéré depuis Windows."); }
        else SetStatus("Mot de passe introuvable ou profil Windows absent.");
    }

    private async Task ConfigureWifiAsync()
    {
        var content = new FormUrlEncodedContent(new Dictionary<string, string> { ["ssid"] = wifiNetworks.Text, ["password"] = wifiPassword.Text });
        using var response = await http.PostAsync($"http://{espHost.Text.Trim()}/configure", content);
        response.EnsureSuccessStatusCode();
        settings = settings with { EspHost = espHost.Text.Trim() }; SaveSettings();
        SetStatus("Wi-Fi envoyé. L’ESP32 redémarre.");
    }
    private async Task TestEspAsync() { await http.GetStringAsync($"http://{espHost.Text.Trim()}/status"); SetStatus("ESP32 connecté."); }
    private async Task PostEspAsync(string path) { using var response = await http.PostAsync($"http://{espHost.Text.Trim()}{path}", null); response.EnsureSuccessStatusCode(); SetStatus("Commande envoyée à l’ESP32."); }

    private async Task ConfigureAutonomousAsync()
    {
        if (autonomousPrinter.SelectedItem is not PrinterProfile profile) return;
        var values = new Dictionary<string, string> {
            ["host"] = profile.Host, ["port"] = profile.Port.ToString(), ["every"] = every.Value.ToString("0"),
            ["skip"] = skip.Value.ToString("0"), ["stop"] = stop.Value.ToString("0"), ["delay"] = ((int)(delay.Value * 1000)).ToString()
        };
        using var response = await http.PostAsync($"http://{espHost.Text.Trim()}/printer-config", new FormUrlEncodedContent(values));
        response.EnsureSuccessStatusCode();
        SetStatus("Mode autonome enregistré dans l’ESP32.");
    }

    private void ScanSerialPorts()
    {
        serialPorts.Items.Clear();
        using var key = Registry.LocalMachine.OpenSubKey(@"HARDWARE\DEVICEMAP\SERIALCOMM");
        if (key != null) foreach (var name in key.GetValueNames()) if (key.GetValue(name) is string portName) serialPorts.Items.Add(portName);
        if (serialPorts.Items.Count > 0) serialPorts.SelectedIndex = 0;
    }

    private async Task FlashEspAsync()
    {
        if (serialPorts.SelectedItem is not string com) { SetStatus("Aucun port USB sélectionné."); return; }
        var resources = Path.Combine(AppContext.BaseDirectory, "Resources");
        var tool = Path.Combine(resources, "esptool.exe");
        if (!File.Exists(tool)) { SetStatus("esptool.exe est absent du paquet Windows."); return; }
        var args = $"--chip esp32c3 --port {com} --baud 460800 write-flash 0x0 \"{Path.Combine(resources, "Hackman3DLayerShot.ino.bootloader.bin")}\" 0x8000 \"{Path.Combine(resources, "Hackman3DLayerShot.ino.partitions.bin")}\" 0x10000 \"{Path.Combine(resources, "Hackman3DLayerShot.ino.bin")}\"";
        SetStatus("Installation du firmware…");
        var process = Process.Start(new ProcessStartInfo(tool, args) { UseShellExecute = false, CreateNoWindow = true });
        if (process == null) return;
        await process.WaitForExitAsync();
        SetStatus(process.ExitCode == 0 ? "Firmware installé." : $"Échec du flashage ({process.ExitCode}).");
    }

    private async Task ExportTimelapseAsync(List<string> images, int fps)
    {
        if (images.Count == 0) { SetStatus("Importez d’abord des photos."); return; }
        var ffmpeg = Path.Combine(AppContext.BaseDirectory, "Resources", "ffmpeg.exe");
        if (!File.Exists(ffmpeg)) { SetStatus("Le moteur vidéo ffmpeg.exe est absent du paquet Windows."); return; }
        using var save = new SaveFileDialog { Filter = "Vidéo MP4|*.mp4", FileName = "timelapse.mp4" };
        if (save.ShowDialog() != DialogResult.OK) return;
        var temp = Path.Combine(Path.GetTempPath(), "Hackman3D-LayerShot-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temp);
        for (var i = 0; i < images.Count; i++) File.Copy(images[i], Path.Combine(temp, $"frame-{i:000000}{Path.GetExtension(images[i])}"));
        var extension = Path.GetExtension(images[0]);
        var args = $"-y -framerate {fps} -i \"{Path.Combine(temp, "frame-%06d" + extension)}\" -vf \"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2\" -c:v libx264 -pix_fmt yuv420p \"{save.FileName}\"";
        var process = Process.Start(new ProcessStartInfo(ffmpeg, args) { UseShellExecute = false, CreateNoWindow = true });
        if (process == null) return;
        await process.WaitForExitAsync();
        SetStatus(process.ExitCode == 0 ? "Timelapse créé." : "Échec de l’export vidéo.");
    }

    private static string Run(string file, string arguments)
    {
        using var process = Process.Start(new ProcessStartInfo(file, arguments) { RedirectStandardOutput = true, UseShellExecute = false, CreateNoWindow = true });
        return process?.StandardOutput.ReadToEnd() ?? "";
    }
    private void SetStatus(string text) => status.Text = text;
    private void LoadSettings()
    {
        try { if (File.Exists(settingsPath)) settings = JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(settingsPath)) ?? new([]); } catch { settings = new([]); }
        espHost.Text = settings.EspHost;
    }
    private void SaveSettings()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(settingsPath)!);
        File.WriteAllText(settingsPath, JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true }));
    }
}
