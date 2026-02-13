"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// Icons
const TelegramIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
  </svg>
);

const SettingsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);

const ChartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 3v18h18"/>
    <path d="m19 9-5 5-4-4-3 3"/>
  </svg>
);

const HistoryIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
    <path d="M3 3v5h5"/>
    <path d="M12 7v5l4 2"/>
  </svg>
);

const RefreshIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
    <path d="M3 3v5h5"/>
    <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
    <path d="M16 16h5v5"/>
  </svg>
);

// Types
interface Settings {
  botEnabled: boolean;
  targetChannel: string;
  appendLink: string;
  dailyLimit: number;
  removeLinks: boolean;
  removeEmojis: boolean;
  sourceGroups: string[];
}

interface PostHistory {
  id: number;
  sourceLink: string;
  targetMessageId: string;
  timestamp: string;
  hasMedia: boolean;
  status: "success" | "failed" | "pending";
}

interface Stats {
  todayPosts: number;
  totalPosts: number;
  dailyLimit: number;
  lastPostTime: string;
  botStatus: "online" | "offline" | "error";
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("settings");
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    botEnabled: true,
    targetChannel: "",
    appendLink: "",
    dailyLimit: 4,
    removeLinks: true,
    removeEmojis: false,
    sourceGroups: [],
  });

  const [stats, setStats] = useState<Stats>({
    todayPosts: 0,
    totalPosts: 0,
    dailyLimit: 4,
    lastPostTime: "-",
    botStatus: "offline",
  });

  const [history, setHistory] = useState<PostHistory[]>([]);
  const [newSourceGroup, setNewSourceGroup] = useState("");

  // Simulated data - in real app, this would come from API
  useEffect(() => {
    // Simulate fetching data
    setStats({
      todayPosts: 2,
      totalPosts: 147,
      dailyLimit: settings.dailyLimit,
      lastPostTime: "14:32",
      botStatus: settings.botEnabled ? "online" : "offline",
    });

    setHistory([
      {
        id: 1,
        sourceLink: "t.me/c/3676643707/17366",
        targetMessageId: "12345",
        timestamp: "2025-02-13 14:32",
        hasMedia: true,
        status: "success",
      },
      {
        id: 2,
        sourceLink: "t.me/msharleycasino/6040",
        targetMessageId: "12346",
        timestamp: "2025-02-13 12:15",
        hasMedia: false,
        status: "success",
      },
      {
        id: 3,
        sourceLink: "t.me/example/1234",
        targetMessageId: "-",
        timestamp: "2025-02-13 10:00",
        hasMedia: true,
        status: "failed",
      },
    ]);
  }, [settings.botEnabled, settings.dailyLimit]);

  const handleSaveSettings = async () => {
    setSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setSaving(false);
  };

  const addSourceGroup = () => {
    if (newSourceGroup && !settings.sourceGroups.includes(newSourceGroup)) {
      setSettings((prev) => ({
        ...prev,
        sourceGroups: [...prev.sourceGroups, newSourceGroup],
      }));
      setNewSourceGroup("");
    }
  };

  const removeSourceGroup = (group: string) => {
    setSettings((prev) => ({
      ...prev,
      sourceGroups: prev.sourceGroups.filter((g) => g !== group),
    }));
  };

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white glow">
              <TelegramIcon />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold gradient-text">
                Telegram Forwarder
              </h1>
              <p className="text-zinc-500 text-sm">Mesaj yonlendirme kontrol paneli</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={stats.botStatus === "online" ? "success" : "destructive"}>
              <span className={`w-2 h-2 rounded-full mr-2 ${stats.botStatus === "online" ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
              {stats.botStatus === "online" ? "Cevrimici" : "Cevrimdisi"}
            </Badge>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="glow">
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Bugun</div>
              <div className="text-3xl font-bold text-emerald-400">
                {stats.todayPosts}/{stats.dailyLimit}
              </div>
              <div className="text-zinc-600 text-xs mt-1">post gonderildi</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Toplam</div>
              <div className="text-3xl font-bold text-zinc-100">{stats.totalPosts}</div>
              <div className="text-zinc-600 text-xs mt-1">post</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Son Post</div>
              <div className="text-3xl font-bold text-zinc-100">{stats.lastPostTime}</div>
              <div className="text-zinc-600 text-xs mt-1">saat</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Kalan</div>
              <div className="text-3xl font-bold text-teal-400">
                {Math.max(0, stats.dailyLimit - stats.todayPosts)}
              </div>
              <div className="text-zinc-600 text-xs mt-1">post hakki</div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full md:w-auto mb-6">
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <SettingsIcon />
              <span className="hidden sm:inline">Ayarlar</span>
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center gap-2">
              <ChartIcon />
              <span className="hidden sm:inline">Istatistikler</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <HistoryIcon />
              <span className="hidden sm:inline">Gecmis</span>
            </TabsTrigger>
          </TabsList>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Bot Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Bot Ayarlari</CardTitle>
                  <CardDescription>Temel bot yapilandirmasi</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Bot Durumu</Label>
                      <p className="text-xs text-zinc-500 mt-1">Botu aktif/pasif yap</p>
                    </div>
                    <Switch
                      checked={settings.botEnabled}
                      onCheckedChange={(checked) =>
                        setSettings((prev) => ({ ...prev, botEnabled: checked }))
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="targetChannel">Hedef Kanal</Label>
                    <Input
                      id="targetChannel"
                      placeholder="@kanaliniz veya -100123456789"
                      value={settings.targetChannel}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, targetChannel: e.target.value }))
                      }
                    />
                    <p className="text-xs text-zinc-500">Mesajlarin iletilecegi kanal</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="appendLink">Eklenecek Link</Label>
                    <Input
                      id="appendLink"
                      placeholder="https://t.me/kanaliniz"
                      value={settings.appendLink}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, appendLink: e.target.value }))
                      }
                    />
                    <p className="text-xs text-zinc-500">Mesaj sonuna eklenecek link</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="dailyLimit">Gunluk Limit</Label>
                    <Input
                      id="dailyLimit"
                      type="number"
                      min="1"
                      max="100"
                      value={settings.dailyLimit}
                      onChange={(e) =>
                        setSettings((prev) => ({
                          ...prev,
                          dailyLimit: parseInt(e.target.value) || 1,
                        }))
                      }
                    />
                    <p className="text-xs text-zinc-500">Gunde maksimum post sayisi</p>
                  </div>
                </CardContent>
              </Card>

              {/* Content Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Icerik Ayarlari</CardTitle>
                  <CardDescription>Mesaj isleme secenekleri</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Linkleri Kaldir</Label>
                      <p className="text-xs text-zinc-500 mt-1">Mesajdaki URL&apos;leri temizle</p>
                    </div>
                    <Switch
                      checked={settings.removeLinks}
                      onCheckedChange={(checked) =>
                        setSettings((prev) => ({ ...prev, removeLinks: checked }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Emojileri Kaldir</Label>
                      <p className="text-xs text-zinc-500 mt-1">Premium emojileri sil</p>
                    </div>
                    <Switch
                      checked={settings.removeEmojis}
                      onCheckedChange={(checked) =>
                        setSettings((prev) => ({ ...prev, removeEmojis: checked }))
                      }
                    />
                  </div>

                  <div className="border-t border-zinc-800 pt-4">
                    <Label>Kaynak Gruplar</Label>
                    <p className="text-xs text-zinc-500 mt-1 mb-3">
                      Mesajlarin alinacagi gruplar
                    </p>
                    <div className="flex gap-2 mb-3">
                      <Input
                        placeholder="Grup ID veya link"
                        value={newSourceGroup}
                        onChange={(e) => setNewSourceGroup(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && addSourceGroup()}
                      />
                      <Button onClick={addSourceGroup} variant="secondary">
                        Ekle
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {settings.sourceGroups.map((group) => (
                        <Badge key={group} variant="secondary" className="pl-3 pr-1 py-1.5">
                          {group}
                          <button
                            onClick={() => removeSourceGroup(group)}
                            className="ml-2 p-1 hover:bg-zinc-600 rounded"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <line x1="18" y1="6" x2="6" y2="18" />
                              <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                          </button>
                        </Badge>
                      ))}
                      {settings.sourceGroups.length === 0 && (
                        <p className="text-zinc-600 text-sm">Henuz grup eklenmedi</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="flex justify-end mt-6">
              <Button onClick={handleSaveSettings} disabled={saving}>
                {saving ? (
                  <>
                    <RefreshIcon />
                    Kaydediliyor...
                  </>
                ) : (
                  "Ayarlari Kaydet"
                )}
              </Button>
            </div>
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats">
            <Card>
              <CardHeader>
                <CardTitle>Istatistikler</CardTitle>
                <CardDescription>Bot performans metrikleri</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-6">
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Bu Hafta</div>
                    <div className="text-4xl font-bold text-emerald-400">24</div>
                    <div className="text-zinc-500 text-sm mt-1">post gonderildi</div>
                  </div>
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Bu Ay</div>
                    <div className="text-4xl font-bold text-teal-400">89</div>
                    <div className="text-zinc-500 text-sm mt-1">post gonderildi</div>
                  </div>
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Basari Orani</div>
                    <div className="text-4xl font-bold text-cyan-400">98%</div>
                    <div className="text-zinc-500 text-sm mt-1">basarili gonderim</div>
                  </div>
                </div>

                <div className="mt-8 p-6 rounded-xl bg-zinc-800/30 border border-zinc-800">
                  <h3 className="text-lg font-semibold mb-4 text-zinc-200">Son 7 Gun</h3>
                  <div className="flex items-end justify-between h-32 gap-2">
                    {[3, 4, 2, 4, 3, 2, 2].map((value, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-2">
                        <div
                          className="w-full bg-gradient-to-t from-emerald-600 to-teal-500 rounded-t-lg transition-all duration-300 hover:opacity-80"
                          style={{ height: `${(value / 4) * 100}%` }}
                        />
                        <span className="text-xs text-zinc-500">
                          {["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"][i]}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Post Gecmisi</CardTitle>
                  <CardDescription>Son yonlendirilen mesajlar</CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <RefreshIcon />
                  Yenile
                </Button>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Kaynak</TableHead>
                      <TableHead>Tarih</TableHead>
                      <TableHead>Medya</TableHead>
                      <TableHead>Durum</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((post) => (
                      <TableRow key={post.id}>
                        <TableCell className="font-mono text-sm">
                          {post.sourceLink}
                        </TableCell>
                        <TableCell>{post.timestamp}</TableCell>
                        <TableCell>
                          {post.hasMedia ? (
                            <Badge variant="secondary">Medya</Badge>
                          ) : (
                            <Badge variant="outline">Metin</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              post.status === "success"
                                ? "success"
                                : post.status === "failed"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {post.status === "success"
                              ? "Basarili"
                              : post.status === "failed"
                              ? "Basarisiz"
                              : "Bekliyor"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="mt-12 text-center text-zinc-600 text-sm">
          <p>Telegram Forwarder Bot v1.0</p>
          <p className="mt-1">Heroku + Netlify + Neon.tech</p>
        </div>
      </div>
    </div>
  );
}
