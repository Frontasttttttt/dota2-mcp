using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace DotaOverlay.Wpf.Models
{
    public class BoardResponse
    {
        [JsonPropertyName("ok")]
        public bool Ok { get; set; }

        [JsonPropertyName("stage")]
        public string? Stage { get; set; }

        [JsonPropertyName("match_id")]
        public string? MatchId { get; set; }

        [JsonPropertyName("clock")]
        public double? Clock { get; set; }

        [JsonPropertyName("timers")]
        public MapTimers? Timers { get; set; }

        [JsonPropertyName("score")]
        public TeamScore? Score { get; set; }

        [JsonPropertyName("you")]
        public HeroYou? You { get; set; }

        [JsonPropertyName("lobby_scout")]
        public LobbyScout? LobbyScout { get; set; }
    }

    public class MapTimers
    {
        [JsonPropertyName("bounty_sec")]
        public int BountySec { get; set; }

        [JsonPropertyName("bounty_fmt")]
        public string BountyFmt { get; set; } = "00:00";

        [JsonPropertyName("river_sec")]
        public int RiverSec { get; set; }

        [JsonPropertyName("river_fmt")]
        public string RiverFmt { get; set; } = "00:00";

        [JsonPropertyName("river_type")]
        public string RiverType { get; set; } = "";

        [JsonPropertyName("lotus_sec")]
        public int LotusSec { get; set; }

        [JsonPropertyName("lotus_fmt")]
        public string LotusFmt { get; set; } = "00:00";

        [JsonPropertyName("wisdom_sec")]
        public int WisdomSec { get; set; }

        [JsonPropertyName("wisdom_fmt")]
        public string WisdomFmt { get; set; } = "00:00";

        [JsonPropertyName("roshan_cave")]
        public string RoshanCave { get; set; } = "";

        [JsonPropertyName("roshan_fmt")]
        public string RoshanFmt { get; set; } = "00:00";

        [JsonPropertyName("roshan_status")]
        public string RoshanStatus { get; set; } = "";

        [JsonPropertyName("tormentor_sec")]
        public int TormentorSec { get; set; }

        [JsonPropertyName("tormentor_fmt")]
        public string TormentorFmt { get; set; } = "00:00";

        [JsonPropertyName("tormentor_status")]
        public string TormentorStatus { get; set; } = "";

        [JsonPropertyName("is_day")]
        public bool IsDay { get; set; }

        [JsonPropertyName("day_night_fmt")]
        public string DayNightFmt { get; set; } = "00:00";

        [JsonPropertyName("neutral_tier")]
        public int NeutralTier { get; set; } = 1;

        [JsonPropertyName("neutral_sec")]
        public int NeutralSec { get; set; }

        [JsonPropertyName("neutral_fmt")]
        public string NeutralFmt { get; set; } = "07:00";

        [JsonPropertyName("neutral_title")]
        public string NeutralTitle { get; set; } = "НЕЙТРАЛКИ Т1";

        [JsonPropertyName("neutral_alert")]
        public bool NeutralAlert { get; set; }

        [JsonPropertyName("stack_sec")]
        public int StackSec { get; set; }

        [JsonPropertyName("stack_fmt")]
        public string StackFmt { get; set; } = "53с";

        [JsonPropertyName("stack_active")]
        public bool StackActive { get; set; }
    }

    public class TeamScore
    {
        [JsonPropertyName("radiant")]
        public int Radiant { get; set; }

        [JsonPropertyName("dire")]
        public int Dire { get; set; }
    }

    public class HeroYou
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";

        [JsonPropertyName("hero_name")]
        public string HeroName { get; set; } = "";

        [JsonPropertyName("gold")]
        public int Gold { get; set; }

        [JsonPropertyName("kda")]
        public string Kda { get; set; } = "0/0/0";

        [JsonPropertyName("health")]
        public int Health { get; set; }

        [JsonPropertyName("max_health")]
        public int MaxHealth { get; set; } = 1;

        [JsonPropertyName("mana")]
        public int Mana { get; set; }

        [JsonPropertyName("max_mana")]
        public int MaxMana { get; set; } = 1;

        [JsonPropertyName("buyback_cost")]
        public int BuybackCost { get; set; }

        [JsonPropertyName("buyback_cooldown")]
        public int BuybackCooldown { get; set; }

        [JsonPropertyName("has_buyback")]
        public bool HasBuyback { get; set; }
    }

    public class LobbyScout
    {
        [JsonPropertyName("radiant")]
        public List<PlayerScout> Radiant { get; set; } = new();

        [JsonPropertyName("dire")]
        public List<PlayerScout> Dire { get; set; } = new();

        [JsonPropertyName("unassigned")]
        public List<PlayerScout> Unassigned { get; set; } = new();

        [JsonPropertyName("summary")]
        public LobbySummary? Summary { get; set; }
    }

    public class LobbySummary
    {
        [JsonPropertyName("suggested_bans")]
        public List<string> SuggestedBans { get; set; } = new();
    }

    public class RecentSummary
    {
        [JsonPropertyName("winrate_pct")]
        public double WinratePct { get; set; }

        [JsonPropertyName("wins")]
        public int Wins { get; set; }

        [JsonPropertyName("losses")]
        public int Losses { get; set; }

        [JsonPropertyName("avg_kda")]
        public double AvgKda { get; set; }
    }

    public class SmurfVerdict
    {
        [JsonPropertyName("badge")]
        public string Badge { get; set; } = "";

        [JsonPropertyName("tips")]
        public List<string> Tips { get; set; } = new();
    }

    public class PlayerScout
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "Player";

        [JsonPropertyName("account_id")]
        public object? AccountId { get; set; }

        [JsonPropertyName("rank_name")]
        public string RankName { get; set; } = "Unranked";

        [JsonPropertyName("threat_level")]
        public string ThreatLevel { get; set; } = "normal";

        [JsonPropertyName("threat_title")]
        public string ThreatTitle { get; set; } = "ОБЫЧНЫЙ ИГРОК";

        [JsonPropertyName("recent_summary")]
        public RecentSummary? RecentSummary { get; set; }

        [JsonPropertyName("smurf_verdict")]
        public SmurfVerdict? SmurfVerdict { get; set; }

        [JsonPropertyName("winrate_pct")]
        public double WinratePct { get; set; }

        [JsonPropertyName("win_loss")]
        public string WinLoss { get; set; } = "-";

        [JsonPropertyName("avg_kda")]
        public double AvgKda { get; set; }

        [JsonPropertyName("recent_heroes")]
        public List<RecentHero> RecentHeroes { get; set; } = new();

        [JsonPropertyName("ban_advice")]
        public string? BanAdvice { get; set; }

        // Presentation helpers for XAML with empty setters for TwoWay compatibility
        public string DisplayBadge
        {
            get => !string.IsNullOrEmpty(SmurfVerdict?.Badge) ? SmurfVerdict.Badge : (ThreatTitle ?? "🟢 ОБЫЧНЫЙ");
            set { }
        }

        public string DisplayWinrate
        {
            get => RecentSummary != null ? $"{RecentSummary.WinratePct:F0}%" : $"{WinratePct:F0}%";
            set { }
        }

        public string DisplayKda
        {
            get => RecentSummary != null ? $"{RecentSummary.AvgKda:F1}" : $"{AvgKda:F1}";
            set { }
        }

        public string DisplayWinLoss
        {
            get => RecentSummary != null ? $"{RecentSummary.Wins}W - {RecentSummary.Losses}L" : WinLoss;
            set { }
        }
    }

    public class RecentHero
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";

        [JsonPropertyName("hero_name")]
        public string? HeroName { get; set; }

        [JsonPropertyName("winrate_pct")]
        public double WinratePct { get; set; }

        [JsonPropertyName("games")]
        public int Games { get; set; }

        public string DisplayHeroName
        {
            get => !string.IsNullOrEmpty(HeroName) ? HeroName : Name;
            set { }
        }
    }
}
