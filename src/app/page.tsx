"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

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

const ChannelsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const TargetIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="6"/>
    <circle cx="12" cy="12" r="2"/>
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

const PlusIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/>
    <path d="M12 5v14"/>
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 6h18"/>
    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
  </svg>
);

const EditIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
    <path d="m15 5 4 4"/>
  </svg>
);

// Types
interface TargetChannel {
  id: number;
  chat_id: string;
  title: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

interface SourceChannel {
  id: number;
  source_chat_id: string;
  source_title: string;
  source_username: string;
  target_chat_id: string;
  target_title: string;
  target_channel_id: number | null;
  target_channel_title: string;
  target_channel_chat_id: string;
  append_link: string;
  daily_limit: number;
  remove_links: boolean;
  remove_emojis: boolean;
  is_active: boolean;
  listen_type: 'direct' | 'link';
  trigger_keywords: string;
  send_link_back: boolean;
  today_posts: number;
  total_posts: number;
  created_at: string;
}

interface PostHistory {
  id: number;
  source_link: string;
  target_message_id: string;
  created_at: string;
  has_media: boolean;
  status: string;
  source_title: string;
  target_title: string;
}

interface Stats {
  today_posts: number;
  total_posts: number;
  active_channels: number;
  bot_status: string;
  bot_enabled: boolean;
  last_post_time: string | null;
  weekly_stats: { date: string; posts: number; success: number }[];
}

const emptySourceChannel: Partial<SourceChannel> = {
  source_chat_id: '',
  source_title: '',
  target_channel_id: null,
  target_chat_id: '',
  target_title: '',
  append_link: '',
  daily_limit: 10,
  remove_links: true,
  remove_emojis: false,
  is_active: true,
  listen_type: 'direct',
  trigger_keywords: '',
  send_link_back: false,
};

const emptyTargetChannel: Partial<TargetChannel> = {
  chat_id: '',
  title: '',
  username: '',
  is_active: true,
};

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("targets");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Data states
  const [targetChannels, setTargetChannels] = useState<TargetChannel[]>([]);
  const [sourceChannels, setSourceChannels] = useState<SourceChannel[]>([]);
  const [history, setHistory] = useState<PostHistory[]>([]);
  const [stats, setStats] = useState<Stats>({
    today_posts: 0,
    total_posts: 0,
    active_channels: 0,
    bot_status: 'offline',
    bot_enabled: true,
    last_post_time: null,
    weekly_stats: [],
  });

  // Dialog states
  const [editingSourceChannel, setEditingSourceChannel] = useState<Partial<SourceChannel> | null>(null);
  const [isSourceDialogOpen, setIsSourceDialogOpen] = useState(false);
  const [editingTargetChannel, setEditingTargetChannel] = useState<Partial<TargetChannel> | null>(null);
  const [isTargetDialogOpen, setIsTargetDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [targetRes, sourceRes, statsRes, postsRes] = await Promise.all([
        fetch('/api/target-channels'),
        fetch('/api/channels'),
        fetch('/api/stats'),
        fetch('/api/posts?limit=50'),
      ]);

      if (targetRes.ok) {
        const targetData = await targetRes.json();
        setTargetChannels(targetData);
      }

      if (sourceRes.ok) {
        const sourceData = await sourceRes.json();
        setSourceChannels(sourceData);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (postsRes.ok) {
        const postsData = await postsRes.json();
        setHistory(postsData);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Target Channel handlers
  const handleSaveTargetChannel = async () => {
    if (!editingTargetChannel) return;

    setSaving(true);
    try {
      const method = editingTargetChannel.id ? 'PUT' : 'POST';
      const response = await fetch('/api/target-channels', {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingTargetChannel),
      });

      if (response.ok) {
        await fetchData();
        setIsTargetDialogOpen(false);
        setEditingTargetChannel(null);
      } else {
        const error = await response.json();
        alert(error.error || 'Bir hata olustu');
      }
    } catch (error) {
      console.error('Error saving target channel:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTargetChannel = async (id: number) => {
    if (!confirm('Bu hedef kanali silmek istediginizden emin misiniz?')) return;

    try {
      const response = await fetch(`/api/target-channels?id=${id}`, { method: 'DELETE' });
      if (response.ok) {
        await fetchData();
      } else {
        const error = await response.json();
        alert(error.error || 'Silinemedi');
      }
    } catch (error) {
      console.error('Error deleting target channel:', error);
    }
  };

  // Source Channel handlers
  const handleSaveSourceChannel = async () => {
    if (!editingSourceChannel) return;

    if (!editingSourceChannel.target_channel_id && !editingSourceChannel.target_chat_id) {
      alert('Lutfen bir hedef kanal secin!');
      return;
    }

    setSaving(true);
    try {
      const method = editingSourceChannel.id ? 'PUT' : 'POST';
      const response = await fetch('/api/channels', {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingSourceChannel),
      });

      if (response.ok) {
        await fetchData();
        setIsSourceDialogOpen(false);
        setEditingSourceChannel(null);
      }
    } catch (error) {
      console.error('Error saving source channel:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSourceChannel = async (id: number) => {
    if (!confirm('Bu dinleme kanalini silmek istediginizden emin misiniz?')) return;

    try {
      const response = await fetch(`/api/channels?id=${id}`, { method: 'DELETE' });
      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error('Error deleting source channel:', error);
    }
  };

  const handleToggleSourceChannel = async (channel: SourceChannel) => {
    try {
      const response = await fetch('/api/channels', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: channel.id, is_active: !channel.is_active }),
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error('Error toggling channel:', error);
    }
  };

  const handleToggleBot = async () => {
    try {
      const newValue = !stats.bot_enabled;
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'bot_enabled', value: newValue ? 'true' : 'false' }),
      });
      setStats(prev => ({ ...prev, bot_enabled: newValue }));
    } catch (error) {
      console.error('Error toggling bot:', error);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getLastPostTime = () => {
    if (!stats.last_post_time) return '-';
    const date = new Date(stats.last_post_time);
    return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  };

  const getTargetChannelName = (channel: SourceChannel) => {
    if (channel.target_channel_title) {
      return channel.target_channel_title;
    }
    if (channel.target_title) {
      return channel.target_title;
    }
    return channel.target_chat_id || 'Hedef Yok';
  };

  return (
    <div className="min-h-screen p-4 md:p-8 bg-zinc-950">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20">
              <TelegramIcon />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                Telegram Forwarder
              </h1>
              <p className="text-zinc-500 text-sm">Mesaj yonlendirme kontrol paneli</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-zinc-400">Bot</span>
              <Switch
                checked={stats.bot_enabled}
                onCheckedChange={handleToggleBot}
              />
            </div>
            <Badge variant={stats.bot_status === "online" ? "success" : "destructive"}>
              <span className={`w-2 h-2 rounded-full mr-2 ${stats.bot_status === "online" ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
              {stats.bot_status === "online" ? "Cevrimici" : "Cevrimdisi"}
            </Badge>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Bugun</div>
              <div className="text-3xl font-bold text-emerald-400">
                {stats.today_posts}
              </div>
              <div className="text-zinc-600 text-xs mt-1">post gonderildi</div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Toplam</div>
              <div className="text-3xl font-bold text-zinc-100">{stats.total_posts}</div>
              <div className="text-zinc-600 text-xs mt-1">post</div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Son Post</div>
              <div className="text-3xl font-bold text-zinc-100">{getLastPostTime()}</div>
              <div className="text-zinc-600 text-xs mt-1">saat</div>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardContent className="p-4">
              <div className="text-zinc-500 text-sm mb-1">Aktif Kanal</div>
              <div className="text-3xl font-bold text-teal-400">
                {stats.active_channels}
              </div>
              <div className="text-zinc-600 text-xs mt-1">dinleniyor</div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full md:w-auto mb-6 bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="targets" className="flex items-center gap-2 data-[state=active]:bg-zinc-800">
              <TargetIcon />
              <span className="hidden sm:inline">Hedef Kanallar</span>
            </TabsTrigger>
            <TabsTrigger value="sources" className="flex items-center gap-2 data-[state=active]:bg-zinc-800">
              <ChannelsIcon />
              <span className="hidden sm:inline">Dinleme Kanallari</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2 data-[state=active]:bg-zinc-800">
              <SettingsIcon />
              <span className="hidden sm:inline">Ayarlar</span>
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center gap-2 data-[state=active]:bg-zinc-800">
              <ChartIcon />
              <span className="hidden sm:inline">Istatistikler</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2 data-[state=active]:bg-zinc-800">
              <HistoryIcon />
              <span className="hidden sm:inline">Gecmis</span>
            </TabsTrigger>
          </TabsList>

          {/* Target Channels Tab */}
          <TabsContent value="targets">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-zinc-100">Hedef Kanallar</CardTitle>
                  <CardDescription>Mesajlarin gonderilecegi kanallar</CardDescription>
                </div>
                <Dialog open={isTargetDialogOpen} onOpenChange={(open) => {
                    if (open && !editingTargetChannel) {
                      setEditingTargetChannel({ ...emptyTargetChannel });
                    }
                    setIsTargetDialogOpen(open);
                    if (!open) {
                      setEditingTargetChannel(null);
                    }
                  }}>
                  <DialogTrigger asChild>
                    <Button onClick={() => {
                      setEditingTargetChannel({ ...emptyTargetChannel });
                      setIsTargetDialogOpen(true);
                    }} className="bg-emerald-600 hover:bg-emerald-700">
                      <PlusIcon />
                      <span className="ml-2">Hedef Ekle</span>
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-zinc-900 border-zinc-800">
                    <DialogHeader>
                      <DialogTitle className="text-zinc-100">
                        {editingTargetChannel?.id ? 'Hedef Kanali Duzenle' : 'Yeni Hedef Kanal Ekle'}
                      </DialogTitle>
                      <DialogDescription>
                        Mesajlarin gonderilecegi kanali ekleyin
                      </DialogDescription>
                    </DialogHeader>

                    {editingTargetChannel && (
                      <div className="grid gap-4 py-4">
                        <div className="space-y-2">
                          <Label htmlFor="target_chat_id">Kanal ID</Label>
                          <Input
                            id="target_chat_id"
                            placeholder="-100123456789 veya @kanaliniz"
                            value={editingTargetChannel.chat_id || ''}
                            onChange={(e) => setEditingTargetChannel(prev => ({ ...prev, chat_id: e.target.value }))}
                            className="bg-zinc-800 border-zinc-700"
                          />
                          <p className="text-xs text-zinc-500">Kanalin ID&apos;si veya @kullaniciadi</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="target_title">Kanal Ismi</Label>
                          <Input
                            id="target_title"
                            placeholder="Kanal Adi"
                            value={editingTargetChannel.title || ''}
                            onChange={(e) => setEditingTargetChannel(prev => ({ ...prev, title: e.target.value }))}
                            className="bg-zinc-800 border-zinc-700"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="target_username">Kullanici Adi (Opsiyonel)</Label>
                          <Input
                            id="target_username"
                            placeholder="@kanaliniz"
                            value={editingTargetChannel.username || ''}
                            onChange={(e) => setEditingTargetChannel(prev => ({ ...prev, username: e.target.value }))}
                            className="bg-zinc-800 border-zinc-700"
                          />
                        </div>
                      </div>
                    )}

                    <DialogFooter>
                      <DialogClose asChild>
                        <Button variant="outline" className="border-zinc-700">Iptal</Button>
                      </DialogClose>
                      <Button onClick={handleSaveTargetChannel} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700">
                        {saving ? 'Kaydediliyor...' : 'Kaydet'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="text-center py-8 text-zinc-500">Yukleniyor...</div>
                ) : targetChannels.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500">
                    <p>Henuz hedef kanal eklenmedi.</p>
                    <p className="text-xs mt-2">Once hedef kanallarinizi ekleyin, sonra dinleme kanallari olusturun.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-zinc-800">
                          <TableHead className="text-zinc-400">Kanal Ismi</TableHead>
                          <TableHead className="text-zinc-400">Kanal ID</TableHead>
                          <TableHead className="text-zinc-400">Kullanici Adi</TableHead>
                          <TableHead className="text-zinc-400 text-right">Islemler</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {targetChannels.map((channel) => (
                          <TableRow key={channel.id} className="border-zinc-800">
                            <TableCell className="font-medium text-zinc-200">
                              {channel.title}
                            </TableCell>
                            <TableCell className="font-mono text-zinc-400 text-sm">
                              {channel.chat_id}
                            </TableCell>
                            <TableCell className="text-zinc-400">
                              {channel.username || '-'}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setEditingTargetChannel(channel);
                                    setIsTargetDialogOpen(true);
                                  }}
                                  className="text-zinc-400 hover:text-zinc-100"
                                >
                                  <EditIcon />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteTargetChannel(channel.id)}
                                  className="text-red-400 hover:text-red-300"
                                >
                                  <TrashIcon />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Source Channels Tab */}
          <TabsContent value="sources">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-zinc-100">Dinleme Kanallari</CardTitle>
                  <CardDescription>Mesajlarin alinacagi kaynaklar</CardDescription>
                </div>
                <Dialog open={isSourceDialogOpen} onOpenChange={(open) => {
                    if (open && !editingSourceChannel) {
                      setEditingSourceChannel({ ...emptySourceChannel });
                    }
                    setIsSourceDialogOpen(open);
                    if (!open) {
                      setEditingSourceChannel(null);
                    }
                  }}>
                  <DialogTrigger asChild>
                    <Button
                      onClick={() => {
                        setEditingSourceChannel({ ...emptySourceChannel });
                        setIsSourceDialogOpen(true);
                      }}
                      className="bg-emerald-600 hover:bg-emerald-700"
                      disabled={targetChannels.length === 0}
                    >
                      <PlusIcon />
                      <span className="ml-2">Dinleme Ekle</span>
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl bg-zinc-900 border-zinc-800">
                    <DialogHeader>
                      <DialogTitle className="text-zinc-100">
                        {editingSourceChannel?.id ? 'Dinleme Kanalini Duzenle' : 'Yeni Dinleme Kanali Ekle'}
                      </DialogTitle>
                      <DialogDescription>
                        Dinleme kanali ayarlarini yapilandirin
                      </DialogDescription>
                    </DialogHeader>

                    {editingSourceChannel && (
                      <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label htmlFor="source_chat_id">Kaynak Kanal ID</Label>
                            <Input
                              id="source_chat_id"
                              placeholder="-100123456789"
                              value={editingSourceChannel.source_chat_id || ''}
                              onChange={(e) => setEditingSourceChannel(prev => ({ ...prev, source_chat_id: e.target.value }))}
                              className="bg-zinc-800 border-zinc-700"
                            />
                            <p className="text-xs text-zinc-500">Dinlenecek kanalin ID&apos;si</p>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor="source_title">Kaynak Ismi</Label>
                            <Input
                              id="source_title"
                              placeholder="Kaynak Kanal"
                              value={editingSourceChannel.source_title || ''}
                              onChange={(e) => setEditingSourceChannel(prev => ({ ...prev, source_title: e.target.value }))}
                              className="bg-zinc-800 border-zinc-700"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="target_channel_id">Hedef Kanal</Label>
                          <Select
                            value={editingSourceChannel.target_channel_id?.toString() || ''}
                            onValueChange={(value) => setEditingSourceChannel(prev => ({
                              ...prev,
                              target_channel_id: value ? parseInt(value) : null
                            }))}
                          >
                            <SelectTrigger className="bg-zinc-800 border-zinc-700">
                              <SelectValue placeholder="Hedef kanal secin..." />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-800 border-zinc-700">
                              {targetChannels.map((tc) => (
                                <SelectItem key={tc.id} value={tc.id.toString()}>
                                  {tc.title} ({tc.chat_id})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-zinc-500">Mesajlarin gonderilecegi hedef kanal</p>
                        </div>

                        <div className="border-t border-zinc-800 pt-4">
                          <h4 className="font-medium text-zinc-200 mb-3">Dinleme Ayarlari</h4>

                          <div className="grid md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label htmlFor="listen_type">Dinleme Turu</Label>
                              <Select
                                value={editingSourceChannel.listen_type || 'direct'}
                                onValueChange={(value) => setEditingSourceChannel(prev => ({ ...prev, listen_type: value as 'direct' | 'link' }))}
                              >
                                <SelectTrigger className="bg-zinc-800 border-zinc-700">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent className="bg-zinc-800 border-zinc-700">
                                  <SelectItem value="direct">Normal (Direkt Mesajlar)</SelectItem>
                                  <SelectItem value="link">Link (Mesaj Baglantilari)</SelectItem>
                                </SelectContent>
                              </Select>
                              <p className="text-xs text-zinc-500">
                                {editingSourceChannel.listen_type === 'link'
                                  ? 'Sadece telegram mesaj linklerini isler'
                                  : 'Tum mesajlari direkt iletir'}
                              </p>
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor="daily_limit">Gunluk Limit</Label>
                              <Input
                                id="daily_limit"
                                type="number"
                                min="1"
                                max="1000"
                                value={editingSourceChannel.daily_limit || 10}
                                onChange={(e) => setEditingSourceChannel(prev => ({ ...prev, daily_limit: parseInt(e.target.value) || 10 }))}
                                className="bg-zinc-800 border-zinc-700"
                              />
                              <p className="text-xs text-zinc-500">Gunde max post sayisi</p>
                            </div>
                          </div>

                          <div className="mt-4 space-y-2">
                            <Label htmlFor="trigger_keywords">Tetikleyici Kelimeler</Label>
                            <Textarea
                              id="trigger_keywords"
                              placeholder="kazanc, bonus, firsat (virgul ile ayirin)"
                              value={editingSourceChannel.trigger_keywords || ''}
                              onChange={(e) => setEditingSourceChannel(prev => ({ ...prev, trigger_keywords: e.target.value }))}
                              className="bg-zinc-800 border-zinc-700"
                            />
                            <p className="text-xs text-zinc-500">
                              Sadece bu kelimeleri iceren mesajlar iletilir. Bos birakirsaniz tum mesajlar iletilir.
                            </p>
                          </div>
                        </div>

                        <div className="border-t border-zinc-800 pt-4">
                          <h4 className="font-medium text-zinc-200 mb-3">Icerik Ayarlari</h4>

                          <div className="space-y-2 mb-4">
                            <Label htmlFor="append_link">Eklenecek Link</Label>
                            <Input
                              id="append_link"
                              placeholder="https://t.me/kanaliniz"
                              value={editingSourceChannel.append_link || ''}
                              onChange={(e) => setEditingSourceChannel(prev => ({ ...prev, append_link: e.target.value }))}
                              className="bg-zinc-800 border-zinc-700"
                            />
                            <p className="text-xs text-zinc-500">Mesaj sonuna eklenecek link</p>
                          </div>

                          <div className="grid md:grid-cols-3 gap-4">
                            <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                              <div>
                                <Label>Linkleri Kaldir</Label>
                                <p className="text-xs text-zinc-500">URL&apos;leri temizle</p>
                              </div>
                              <Switch
                                checked={editingSourceChannel.remove_links !== false}
                                onCheckedChange={(checked) => setEditingSourceChannel(prev => ({ ...prev, remove_links: checked }))}
                              />
                            </div>

                            <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                              <div>
                                <Label>Emojileri Kaldir</Label>
                                <p className="text-xs text-zinc-500">Emojileri sil</p>
                              </div>
                              <Switch
                                checked={editingSourceChannel.remove_emojis === true}
                                onCheckedChange={(checked) => setEditingSourceChannel(prev => ({ ...prev, remove_emojis: checked }))}
                              />
                            </div>

                            <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                              <div>
                                <Label>Link Geri Gonder</Label>
                                <p className="text-xs text-zinc-500">Hedef linkini kaynaga at</p>
                              </div>
                              <Switch
                                checked={editingSourceChannel.send_link_back === true}
                                onCheckedChange={(checked) => setEditingSourceChannel(prev => ({ ...prev, send_link_back: checked }))}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    <DialogFooter>
                      <DialogClose asChild>
                        <Button variant="outline" className="border-zinc-700">Iptal</Button>
                      </DialogClose>
                      <Button onClick={handleSaveSourceChannel} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700">
                        {saving ? 'Kaydediliyor...' : 'Kaydet'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {targetChannels.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500">
                    <p>Once hedef kanal eklemeniz gerekiyor.</p>
                    <Button
                      variant="outline"
                      className="mt-4 border-zinc-700"
                      onClick={() => setActiveTab('targets')}
                    >
                      Hedef Kanallara Git
                    </Button>
                  </div>
                ) : loading ? (
                  <div className="text-center py-8 text-zinc-500">Yukleniyor...</div>
                ) : sourceChannels.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500">
                    Henuz dinleme kanali eklenmedi.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-zinc-800">
                          <TableHead className="text-zinc-400">Kaynak</TableHead>
                          <TableHead className="text-zinc-400">Hedef</TableHead>
                          <TableHead className="text-zinc-400">Tur</TableHead>
                          <TableHead className="text-zinc-400">Limit</TableHead>
                          <TableHead className="text-zinc-400">Bugun</TableHead>
                          <TableHead className="text-zinc-400">Durum</TableHead>
                          <TableHead className="text-zinc-400 text-right">Islemler</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sourceChannels.map((channel) => (
                          <TableRow key={channel.id} className="border-zinc-800">
                            <TableCell>
                              <div>
                                <div className="font-medium text-zinc-200">
                                  {channel.source_title || 'Kanal'}
                                </div>
                                <div className="text-xs text-zinc-500 font-mono">
                                  {channel.source_chat_id}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div>
                                <div className="font-medium text-zinc-200">
                                  {getTargetChannelName(channel)}
                                </div>
                                <div className="text-xs text-zinc-500 font-mono">
                                  {channel.target_channel_chat_id || channel.target_chat_id}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant={channel.listen_type === 'link' ? 'secondary' : 'outline'}>
                                {channel.listen_type === 'link' ? 'Link' : 'Normal'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-zinc-300">
                              {channel.daily_limit}
                            </TableCell>
                            <TableCell>
                              <span className="text-emerald-400">{channel.today_posts || 0}</span>
                              <span className="text-zinc-500">/{channel.daily_limit}</span>
                            </TableCell>
                            <TableCell>
                              <Switch
                                checked={channel.is_active}
                                onCheckedChange={() => handleToggleSourceChannel(channel)}
                              />
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setEditingSourceChannel(channel);
                                    setIsSourceDialogOpen(true);
                                  }}
                                  className="text-zinc-400 hover:text-zinc-100"
                                >
                                  <EditIcon />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeleteSourceChannel(channel.id)}
                                  className="text-red-400 hover:text-red-300"
                                >
                                  <TrashIcon />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-zinc-100">Genel Ayarlar</CardTitle>
                  <CardDescription>Bot yapilandirmasi</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg">
                    <div>
                      <Label className="text-zinc-200">Bot Durumu</Label>
                      <p className="text-xs text-zinc-500 mt-1">Botu aktif/pasif yap</p>
                    </div>
                    <Switch
                      checked={stats.bot_enabled}
                      onCheckedChange={handleToggleBot}
                    />
                  </div>

                  <div className="p-4 bg-zinc-800/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-zinc-200">Bot Durumu</Label>
                      <Badge variant={stats.bot_status === "online" ? "success" : "destructive"}>
                        {stats.bot_status === "online" ? "Cevrimici" : "Cevrimdisi"}
                      </Badge>
                    </div>
                    <p className="text-xs text-zinc-500">
                      Bot&apos;un Heroku&apos;da calisma durumu
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-zinc-100">Hakkinda</CardTitle>
                  <CardDescription>Sistem bilgileri</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 bg-zinc-800/50 rounded-lg">
                    <div className="text-sm text-zinc-400 mb-1">Versiyon</div>
                    <div className="text-zinc-200">1.1.0</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 rounded-lg">
                    <div className="text-sm text-zinc-400 mb-1">Bot</div>
                    <div className="text-zinc-200">Python Telethon @ Heroku</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 rounded-lg">
                    <div className="text-sm text-zinc-400 mb-1">Dashboard</div>
                    <div className="text-zinc-200">Next.js @ Netlify</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 rounded-lg">
                    <div className="text-sm text-zinc-400 mb-1">Veritabani</div>
                    <div className="text-zinc-200">PostgreSQL @ Neon.tech</div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-zinc-100">Istatistikler</CardTitle>
                <CardDescription>Bot performans metrikleri</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-6">
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Bu Hafta</div>
                    <div className="text-4xl font-bold text-emerald-400">
                      {stats.weekly_stats.reduce((acc, s) => acc + Number(s.posts || 0), 0)}
                    </div>
                    <div className="text-zinc-500 text-sm mt-1">post gonderildi</div>
                  </div>
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Toplam</div>
                    <div className="text-4xl font-bold text-teal-400">{stats.total_posts}</div>
                    <div className="text-zinc-500 text-sm mt-1">post gonderildi</div>
                  </div>
                  <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700">
                    <div className="text-zinc-400 text-sm mb-2">Aktif Kanallar</div>
                    <div className="text-4xl font-bold text-cyan-400">{stats.active_channels}</div>
                    <div className="text-zinc-500 text-sm mt-1">kanal dinleniyor</div>
                  </div>
                </div>

                {stats.weekly_stats.length > 0 && (
                  <div className="mt-8 p-6 rounded-xl bg-zinc-800/30 border border-zinc-800">
                    <h3 className="text-lg font-semibold mb-4 text-zinc-200">Son 7 Gun</h3>
                    <div className="flex items-end justify-between h-32 gap-2">
                      {stats.weekly_stats.map((stat, i) => {
                        const maxPosts = Math.max(...stats.weekly_stats.map(s => Number(s.posts) || 1));
                        const height = ((Number(stat.posts) || 0) / maxPosts) * 100;
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center gap-2">
                            <div
                              className="w-full bg-gradient-to-t from-emerald-600 to-teal-500 rounded-t-lg transition-all duration-300 hover:opacity-80"
                              style={{ height: `${Math.max(height, 5)}%` }}
                            />
                            <span className="text-xs text-zinc-500">
                              {new Date(stat.date).toLocaleDateString('tr-TR', { weekday: 'short' })}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-zinc-100">Post Gecmisi</CardTitle>
                  <CardDescription>Son yonlendirilen mesajlar</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={fetchData} className="border-zinc-700">
                  <RefreshIcon />
                  <span className="ml-2">Yenile</span>
                </Button>
              </CardHeader>
              <CardContent>
                {history.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500">
                    Henuz post gecmisi yok
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-zinc-800">
                        <TableHead className="text-zinc-400">Kaynak</TableHead>
                        <TableHead className="text-zinc-400">Tarih</TableHead>
                        <TableHead className="text-zinc-400">Medya</TableHead>
                        <TableHead className="text-zinc-400">Durum</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.map((post) => (
                        <TableRow key={post.id} className="border-zinc-800">
                          <TableCell>
                            <div>
                              <div className="font-medium text-zinc-200">
                                {post.source_title || 'Kaynak'}
                              </div>
                              <div className="font-mono text-xs text-zinc-500">
                                {post.source_link}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-zinc-300">{formatDate(post.created_at)}</TableCell>
                          <TableCell>
                            {post.has_media ? (
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
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="mt-12 text-center text-zinc-600 text-sm">
          <p>Telegram Forwarder Bot v1.1</p>
          <p className="mt-1">Heroku + Netlify + Neon.tech</p>
        </div>
      </div>
    </div>
  );
}
