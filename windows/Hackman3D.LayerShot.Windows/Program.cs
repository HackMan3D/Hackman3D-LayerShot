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
    private readonly Label status = new() { Dock = DockStyle.Bottom, Height = 32, ForeColor = Color.Silver, Padding = new Padding(12, 7, 0, 0), Text = "Prêt" };
    private readonly Dictionary<string, Control> cards = [];
    private AppSettings settings = new([]);
    private readonly string settingsPath;
    private readonly System.Windows.Forms.Timer pollTimer = new() { Interval = 2000 };

    public MainForm()
    {
        Text = "Hackman3D LayerShot";
        MinimumSize = new Size(980, 680);
        Size = new Size(1180, 780);
        BackColor = Color.FromArgb(20, 20, 23);
        ForeColor = Color.WhiteSmoke;
        Font = new Font("Segoe UI", 10);
        settingsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Hackman3D", "LayerShot", "settings.json");

        models.Items.AddRange(["K2 / K2 Plus", "K1 / K1C / K1 Max", "SPARKX i7 / i7 Color Combo", "Ender-3 V3 / KE", "CR-10 SE", "Klipper / Moonraker"]);
        models.SelectedIndex = 0;

        var tabs = new TabControl { Dock = DockStyle.Fill, Padding = new Point(18, 8) };
        tabs.TabPages.Add(MakeDashboardPage());
        tabs.TabPages.Add(MakeSetupPage());
        tabs.TabPages.Add(MakeTimelapsePage());
        tabs.TabPages.Add(MakeAboutPage());
        Controls.Add(tabs);
        Controls.Add(status);

        LoadSettings();
        RefreshDashboard();
        pollTimer.Tick += async (_, _) => await PollAllAsync();
        pollTimer.Start();
        Shown += async (_, _) => await PollAllAsync();
    }

    private TabPage MakeDashboardPage()
    {
        var page = Page("Imprimantes");
        var header = new Label { Text = "Imprimantes Creality", Dock = DockStyle.Top, Height = 64, Font = new Font(Font.FontFamily, 24, FontStyle.Bold), Padding = new Padding(16, 16, 0, 0) };
        page.Controls.Add(dashboard);
        page.Controls.Add(header);
        return page;
    }

    private TabPage MakeSetupPage()
    {
        var page = Page("Installation");
        var flow = Stack();
        flow.Controls.Add(Group("Ajouter une imprimante",
            Field("Nom", printerName), Field("Modèle", models), Field("Adresse IP", printerHost), Field("Port", printerPort),
            Button("Tester et enregistrer", async (_, _) => await AddPrinterAsync())));
        flow.Controls.Add(Group("ESP32-C3 · Wi-Fi et Bluetooth",
            Field("Adresse de l’ESP32", espHost), Field("Réseau Wi-Fi", wifiNetworks), Field("Mot de passe", wifiPassword),
            Button("Rechercher les réseaux", (_, _) => ScanWifi()),
            Button("Utiliser le mot de passe Windows", (_, _) => ReadWifiPassword()),
            Button("Envoyer le Wi-Fi", async (_, _) => await ConfigureWifiAsync()),
            Button("Tester l’ESP32", async (_, _) => await TestEspAsync()),
            Button("Activer l’appairage iPhone", async (_, _) => await PostEspAsync("/pair")),
            Button("Oublier l’iPhone", async (_, _) => await PostEspAsync("/reset-bonds"))));
        flow.Controls.Add(Group("Déclenchement autonome",
            new Label { AutoSize = true, MaximumSize = new Size(760, 0), Text = "Ces paramètres sont enregistrés dans l’ESP32. Le PC peut ensuite être éteint pendant l’impression." },
            Field("Imprimante surveillée", autonomousPrinter), Field("Une photo toutes les couches", every),
            Field("Ignorer les premières couches", skip), Field("Arrêter après (0 = jamais)", stop),
            Field("Stabilisation (secondes)", delay),
            Button("Enregistrer dans l’ESP32", async (_, _) => await ConfigureAutonomousAsync())));
        flow.Controls.Add(Group("Firmware ESP32-C3",
            Field("Port USB", serialPorts), Button("Détecter la carte", (_, _) => ScanSerialPorts()),
            Button("Installer / mettre à jour", async (_, _) => await FlashEspAsync())));
        page.Controls.Add(flow);
        return page;
    }

    private TabPage MakeTimelapsePage()
    {
        var page = Page("Timelapse");
        var flow = Stack();
        var selected = new Label { AutoSize = true, Text = "Aucune photo sélectionnée" };
        var fps = new NumericUpDown { Minimum = 12, Maximum = 60, Value = 30 };
        var images = new List<string>();
        flow.Controls.Add(Group("Photos",
            selected,
            Button("Importer les photos…", (_, _) => {
                using var dialog = new OpenFileDialog { Multiselect = true, Filter = "Images|*.jpg;*.jpeg;*.png;*.webp" };
                if (dialog.ShowDialog() == DialogResult.OK) { images = dialog.FileNames.Order().ToList(); selected.Text = $"{images.Count} photo(s) sélectionnée(s)"; }
            }),
            Field("Images par seconde", fps),
            Button("Créer le MP4…", async (_, _) => await ExportTimelapseAsync(images, (int)fps.Value))));
        page.Controls.Add(flow);
        return page;
    }

    private TabPage MakeAboutPage()
    {
        var page = Page("Hackman3D");
        var flow = Stack();
        flow.Controls.Add(Group("Hackman3D LayerShot",
            new Label { AutoSize = true, MaximumSize = new Size(760, 0), Text = "Développé et partagé gratuitement. Les dons, retours et abonnements aux réseaux sociaux aident à poursuivre son développement." },
            Link("Creality Cloud", "https://www.crealitycloud.com/user/5221417142"),
            Link("TikTok", "https://www.tiktok.com/@hackman3d"),
            Link("Instagram", "https://www.instagram.com/hackman_3dprint/"),
            Link("YouTube", "https://www.youtube.com/@hackman3D"),
            Link("E-mail / feedback", "mailto:hackman3d.pro@gmail.com"),
            Link("Soutenir avec PayPal", "https://paypal.me/Hackman3D"),
            new Label { AutoSize = true, Text = "Créé, designé et codé par Hackman3D" }));
        page.Controls.Add(flow);
        return page;
    }

    private static TabPage Page(string title) => new(title) { BackColor = Color.FromArgb(20, 20, 23), ForeColor = Color.WhiteSmoke };
    private static FlowLayoutPanel Stack() => new() { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, Padding = new Padding(16) };
    private static FlowLayoutPanel Group(string title, params Control[] controls)
    {
        var group = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoSize = true, Width = 850, Padding = new Padding(16), Margin = new Padding(0, 0, 0, 14), BackColor = Color.FromArgb(32, 32, 36) };
        group.Controls.Add(new Label { Text = title, AutoSize = true, Font = new Font("Segoe UI", 15, FontStyle.Bold), Margin = new Padding(0, 0, 0, 10) });
        group.Controls.AddRange(controls);
        return group;
    }
    private static FlowLayoutPanel Field(string label, Control input)
    {
        var row = new FlowLayoutPanel { FlowDirection = FlowDirection.LeftToRight, Width = 780, Height = 42, WrapContents = false };
        row.Controls.Add(new Label { Text = label, Width = 330, Padding = new Padding(0, 9, 0, 0) });
        row.Controls.Add(input);
        return row;
    }
    private static Button Button(string text, EventHandler action)
    {
        var button = new Button { Text = text, AutoSize = true, MinimumSize = new Size(160, 34), BackColor = Color.FromArgb(10, 132, 255), ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        button.Click += action;
        return button;
    }
    private static LinkLabel Link(string text, string url)
    {
        var link = new LinkLabel { Text = text, AutoSize = true, LinkColor = Color.FromArgb(100, 190, 255) };
        link.Click += (_, _) => Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        return link;
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
            var box = new GroupBox { Text = $"{profile.Name} · {profile.Model}", Width = 510, Height = 230, ForeColor = Color.WhiteSmoke, BackColor = Color.FromArgb(32, 32, 36), Padding = new Padding(14) };
            var content = new Label { Dock = DockStyle.Fill, Font = new Font("Segoe UI", 11), Text = $"{profile.Host}:{profile.Port}\n\nConnexion…" };
            var remove = new Button { Text = "Retirer", Dock = DockStyle.Bottom, Height = 30 };
            remove.Click += (_, _) => { settings.Printers.Remove(profile); SaveSettings(); RefreshDashboard(); };
            var camera = new Button { Text = "Caméra", Dock = DockStyle.Bottom, Height = 30 };
            camera.Click += async (_, _) => await OpenCameraAsync(profile);
            box.Controls.Add(content); box.Controls.Add(camera); box.Controls.Add(remove);
            dashboard.Controls.Add(box);
            cards[$"{profile.Host}:{profile.Port}"] = content;
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
                label.Text = $"{profile.Host}:{profile.Port}\n\nÉtat : {state}\nCouche : {layer} / {total}\nProgression : {progress:P0}\n{file}";
            }
            catch { label.Text = $"{profile.Host}:{profile.Port}\n\nHors ligne"; }
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
