# Agentic FilmOps — 仕様書 (SPEC v0.1)

> 本ドキュメントは `docs/IDEA.md` の構想をベースに、ハッカソン実装のための機能仕様・技術仕様・データ仕様として再構成したものです。

---

## 0. ドキュメント情報

| 項目 | 内容 |
| --- | --- |
| プロダクト名 | Agentic FilmOps |
| バージョン | v0.1 (Hackathon MVP) |
| ベース資料 | `docs/IDEA.md` |
| 想定期間 | ハッカソン期間内（数日〜1週間） |
| デモ時間 | 約4分 |

---

## 1. プロダクトビジョン

**Agentic FilmOps** は、映画制作に関わる人・機材・ロケーション・予算・脚本・外部環境（天候など）をAIからアクセス可能な **Production Resource Network** として統合し、制作中に発生する変更（天候リスクなど）に対して複数のAI Agentが協調して影響分析・関係者への問い合わせ・再計画を行う **Production Control Tower** である。

### コンセプト

> Every production resource becomes AI-accessible through MCP.
> When reality changes, agents coordinate the entire production in real time.

### 実現するループ

```text
Observe → Reason → Coordinate → Re-plan → Human Approve → Execute
```

単なるスケジューラーではなく、上記6段階を閉ループとして体験できることが本プロダクトの核心的価値である。

---

## 2. デモスコープ（ハッカソンで見せる範囲）

映画制作システム全体は作らない。以下の**単一シナリオ**を完成度高く実装し、3〜5分のライブデモとして成立させることをゴールとする。

### 2.1 デモシナリオ

撮影前日、屋外 **Scene 42** について豪雨予報（雨量確率92%）が発生する。

```text
Weather MCP
    ↓
Weather Agent
    ↓
Production Orchestrator（影響分析）
    ↓
┌────────────┬────────────┬────────────┐
Actor Agent  Equipment    Location     Budget
             Agent        Agent        Agent
    ↓            ↓            ↓            ↓
Manager      Rental       Location     Cost DB
問い合わせ    Company       Manager
    ↓            ↓            ↓
回答取得       回答取得       回答取得
    └────────────┬────────────┘
                 ↓
        Production Resource Graph
                 ↓
          Schedule Agent（再計画）
                 ↓
          代替案 A / B / C
                 ↓
        Producer Dashboard
                 ↓
             APPROVE
                 ↓
         Production Update（実行）
```

### 2.2 デモ時間構成（目安 約4分）

| 時間 | 内容 |
| ---: | --- |
| 0:00 | Production Dashboard 表示 |
| 0:20 | Weather Alert 発生 |
| 0:40 | Impact Analysis 開始 |
| 1:00 | Multi-Agent 並行動作 |
| 1:30 | MCP アクセス表示 |
| 1:50 | Manager 問い合わせ |
| 2:20 | 回答取得 |
| 2:40 | Replanning（再計画） |
| 3:10 | Option A/B/C 提示 |
| 3:30 | Producer Approval |
| 3:45 | MCP Execution |
| 4:00 | Incident Resolved |

---

## 3. システムアーキテクチャ

### 3.1 全体構成

```text
                    ┌───────────────────────┐
                    │  Producer Dashboard   │
                    │  React / Next.js      │
                    └───────────┬───────────┘
                                │
                         WebSocket / API
                                │
                    ┌───────────▼───────────┐
                    │ PRODUCTION            │
                    │ ORCHESTRATOR          │
                    │ Gemini + Google ADK   │
                    └───────────┬───────────┘
                                │
                           MCP Layer
                                │
        ┌──────────┬────────────┼────────────┬──────────┐
        ▼          ▼            ▼            ▼          ▼
   ACTOR MCP   EQUIPMENT    LOCATION      SCRIPT     WEATHER
                  MCP          MCP          MCP         MCP
        │          │            │            │          │
        ▼          ▼            ▼            ▼          ▼
 Actor Agent  Equipment     Location      Script     Weather
              Agent         Agent         Agent      Agent
        │          │            │
        ▼          ▼            ▼
   Manager     Rental       Location
    Mock       Company       Manager
               Mock           Mock
                                │
                    ┌───────────▼───────────┐
                    │ Production Resource  │
                    │ Graph                │
                    └───────────────────────┘
```

### 3.2 アーキテクチャ原則（必須制約）

**UIから各Agentを直接呼び出してはならない。** すべての操作は以下の経路を通す。

```text
Dashboard → Orchestrator → MCP → Resource / Agent
```

この制約により「すべてのProduction ResourceがMCPを介してAIに接続されている」というコンセプトを明確に保つ。UI実装・Orchestrator実装のいずれにおいても、この経路を迂回する直接呼び出しは禁止とする。

### 3.3 Agent と MCP の役割分離

デモ中に審査員へ説明できるよう、以下の分離を厳密に維持する。

```text
Agent = Reasoning（推論・判断）
MCP   = Access / Action（アクセス・実行）
```

---

## 4. データモデル（Production Resource Graph）

システムの中心データモデル。Scene を起点に Actor / Equipment / Location / Crew が接続されるグラフ構造。

### 4.1 Scene

```json
{
  "scene_id": "SC-042",
  "name": "Rooftop confrontation",
  "type": "outdoor",
  "duration_hours": 4,
  "actors": ["ACT-001", "ACT-002"],
  "location": "LOC-003",
  "equipment": ["EQ-001", "EQ-004"],
  "crew": ["CREW-001"],
  "scheduled": "2026-09-02T14:00"
}
```

### 4.2 Actor

```json
{
  "id": "ACT-001",
  "name": "Emma Carter",
  "manager": "MGR-001",
  "availability": [],
  "status": "confirmed"
}
```

### 4.3 Equipment

```json
{
  "id": "EQ-001",
  "name": "ARRI Alexa 35",
  "vendor": "Cinema Rental Tokyo",
  "availability": [],
  "daily_cost": 1200
}
```

### 4.4 グラフ構造イメージ

```text
                 SCENE 42
                    │
       ┌────────────┼─────────────┐
       ↓            ↓             ↓
     Emma         Daniel       Rooftop
       │            │             │
    Manager      Manager       Location
       │                          Owner
       ↓
    Agency

                 SCENE 42
                    │
             ┌──────┴──────┐
             ↓             ↓
         Alexa 35       Lighting Kit
             │
             ↓
       Rental Company
```

---

## 5. MCP サーバー仕様

ハッカソンでは実サービスに接続せず **Mock MCP Server** とする。ただし「本物のAPIに置き換え可能なInterface」として設計することを必須要件とする（ツールのシグネチャ・戻り値のスキーマは本番想定のまま固定する）。

### 5.1 Actor MCP

| Tool | 用途 |
| --- | --- |
| `get_actor()` | Actor情報取得 |
| `get_actor_availability()` | 空き状況取得 |
| `get_actor_constraints()` | 契約制約取得 |
| `contact_manager()` | マネージャーへ問い合わせ |
| `get_contact_status()` | 問い合わせステータス確認 |
| `get_manager_response()` | マネージャー回答取得 |
| `hold_actor()` | 仮押さえ |
| `confirm_actor()` | 確定 |

### 5.2 Equipment MCP

| Tool | 用途 |
| --- | --- |
| `get_equipment()` | 機材情報取得 |
| `check_availability()` | 空き確認 |
| `request_extension()` | 延長依頼 |
| `request_reservation()` | 予約依頼 |
| `get_vendor_response()` | ベンダー回答取得 |
| `reserve_equipment()` | 予約確定 |

### 5.3 Location MCP

| Tool | 用途 |
| --- | --- |
| `get_location()` | ロケーション情報取得 |
| `check_availability()` | 空き確認 |
| `contact_location_manager()` | ロケーション管理者へ問い合わせ |
| `find_alternative_locations()` | 代替ロケーション検索 |
| `hold_location()` | 仮押さえ |
| `confirm_location()` | 確定 |

### 5.4 Weather MCP

| Tool | 用途 |
| --- | --- |
| `get_forecast()` | 天気予報取得 |
| `get_weather_risk()` | 天候リスク評価取得 |
| `subscribe_weather_alert()` | 天候アラート購読 |

### 5.5 Script MCP

| Tool | 用途 |
| --- | --- |
| `get_scene()` | シーン情報取得 |
| `get_scene_requirements()` | シーン要件取得 |
| `get_scene_dependencies()` | シーン依存関係取得 |
| `get_continuity_constraints()` | 継続性（連続性）制約取得 |

### 5.6 Budget MCP

| Tool | 用途 |
| --- | --- |
| `get_current_budget()` | 現行予算取得 |
| `estimate_change_cost()` | 変更コスト見積もり |
| `calculate_overtime()` | 残業コスト計算 |
| `calculate_vendor_cost()` | ベンダーコスト計算 |

---

## 6. Agent 仕様

Agent と MCP Server は明確に分離する（[3.3](#33-agent-と-mcp-の役割分離) 参照）。

### 6.1 Production Orchestrator

システム全体の司令塔。Gemini を使用。

**責務パイプライン:**

```text
Event detection
  ↓
Determine affected resources
  ↓
Delegate investigation
  ↓
Collect responses
  ↓
Generate alternatives
  ↓
Evaluate alternatives
  ↓
Request human approval
  ↓
Execute approved plan
```

### 6.2 Actor Agent

役者関連の調整を担当。

**例: Orchestratorからの依頼**

> Can Emma Carter move Scene 42 to Wednesday afternoon?

**処理フロー:**

```text
1. Actor MCP → calendar確認
2. Contract constraint確認
3. Managerへの問い合わせが必要と判断
4. contact_manager()
5. WAITING_EXTERNAL_RESPONSE
6. Manager Mock response
7. Parse response
8. AVAILABLE_AFTER_16:00
9. Orchestratorへ返却
```

### 6.3 Equipment Agent / Location Agent / Budget Agent / Schedule Agent

同様に MCP を介してそれぞれのドメイン（機材・ロケーション・予算・スケジュール）の調整・評価を担当する。詳細フローは Actor Agent に準ずる。

---

## 7. 疑似遅延（Latency Simulation）仕様

**重要な非機能要件。** すべてのレスポンスが即時（0.1秒未満）で返るとAPI呼び出しの羅列にしか見えず、Agenticな体験として審査員に伝わらない。意図的に遅延を挿入する。

### 7.1 Actor Agent の遅延パターン例

```text
Checking calendar...        ↓ 1.2 sec
Checking contract...        ↓ 0.8 sec
Contacting manager...       ↓
WAITING FOR MANAGER         ↓ 4 sec
Manager replied
"Emma can make it after 4 PM."
                             ↓
Parsing response...          ↓
AVAILABLE
```

### 7.2 Equipment Agent の遅延パターン例

```text
Checking inventory
       ↓
Contacting rental company
       ↓
WAITING
       ↓
Vendor confirmed
```

各 Agent の遅延値は設定可能（config化）とし、デモ中に調整できるようにする。

---

## 8. イベントストリーム仕様

バックエンドは全Agentイベントを記録し、WebSocket/SSE経由でDashboardへリアルタイム配信する。UIのリアリティを支える基盤機能。

### 8.1 イベントスキーマ

```json
{
  "timestamp": "14:07:13",
  "agent": "ActorAgent",
  "type": "EXTERNAL_REQUEST",
  "status": "WAITING",
  "message": "Contacting Emma Carter's manager",
  "resource": "ACT-001"
}
```

### 8.2 ステータス種別

```text
QUEUED
THINKING
QUERYING_MCP
WAITING_EXTERNAL
RESPONSE_RECEIVED
ANALYZING
COMPLETED
FAILED
```

### 8.3 配信方式

- WebSocket または SSE でDashboardへプッシュ配信
- 配信遅延は [7章](#7-疑似遅延latency-simulation仕様) の各Agent遅延と同期させる

---

## 9. UI仕様

### 9.1 Main Dashboard

```text
┌──────────────────────────────────────────────────────────────┐
│ AGENTIC FILMOPS                     PRODUCTION DAY 27 / 54   │
├──────────────────────────────────────────────────────────────┤
│ PRODUCTION HEALTH                                            │
│ Schedule       Budget         Scenes        Risk             │
│   94%          $12.4M         82/143         MEDIUM           │
├──────────────────────────────────────────────────────────────┤
│ 🔴 ACTIVE INCIDENT                                           │
│ WEATHER RISK                                                 │
│ Scene 42 — Rooftop Confrontation                             │
│ Tomorrow 14:00                                               │
│ Heavy rain probability: 92%                                 │
│  [ START AI IMPACT ANALYSIS ]                               │
├──────────────────────────────────────────────────────────────┤
│ TODAY                                                        │
│ Scene 38 ██████ COMPLETED                                    │
│ Scene 39 ██████ COMPLETED                                    │
│ Scene 40 ██████ SHOOTING                                     │
└──────────────────────────────────────────────────────────────┘
```

要素:
- Production Health サマリー（Schedule / Budget / Scenes / Risk）
- Active Incident カード（天候リスク検知）
- Impact Analysis 起動ボタン
- 当日シーン進行状況

### 9.2 Agent Live View

「START AI IMPACT ANALYSIS」押下でAgent viewへ遷移する。

```text
AI COORDINATION

Production Orchestrator
● Analyzing impact...

        │
 ┌──────┼────────┬──────────┬───────────┐
 ↓      ↓        ↓          ↓           ↓
Actor  Actor   Equipment  Location    Budget
Emma   Daniel    Agent      Agent      Agent
 ●       ●        ●           ●          ○
Checking Checking Checking   Searching   Waiting
```

各Agentノードの状態（●稼働中 / ○待機）をリアルタイムに更新する。

### 9.3 MCP Activity Monitor

画面右側に配置。「MCPで全部つながっている」ことを審査員が視覚的に理解できる最重要パネル。

```text
LIVE MCP ACTIVITY

14:03:01
→ weather.get_forecast()
14:03:02
← Rain probability 92%
14:03:04
→ script.get_scene(SC-042)
14:03:05
← 7 resource dependencies
14:03:06
→ actor.get_availability(ACT-001)
14:03:07
← Requires manager confirmation
14:03:08
→ actor.contact_manager(MGR-001)
14:03:09
⏳ Waiting for external response...
```

### 9.4 Resource Network View

**本プロダクトの主役画面。** 通常のダッシュボード以上にこの画面を中心に据える。

```text
                     GEMINI
                  ORCHESTRATOR
                       ◎
                       │
                      MCP
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
     ACTORS         EQUIPMENT        LOCATIONS
       ●               ●                ●
     Emma           Alexa 35         Rooftop
       │               │                │
    Manager          Vendor            Owner
       ●               ●                ●

                SCRIPT ─── SCENE 42
                       │
                     WEATHER
                       ●
```

豪雨イベント発生時、**Scene 42 → Actor → Manager → Equipment → Vendor → Location** の順にAgentのアクセスがネットワーク上をリアルタイムに伝播するアニメーションを表示する。アクセス中のノード・エッジを光らせる演出を行う。

この Resource Network View を、右側の **Agent reasoning log + MCP call stream** と同期させることで、説明なしに以下を理解させる:

> 「Geminiが中央にいて、MCPを介して映画制作の人・モノ・場所すべてにアクセスし、現実世界とやり取りしながら再計画している」

### 9.5 External Communication Mock

役者マネージャー等とのやり取りを画面に表示し、非構造化コミュニケーションがLLMによって構造化データへ変換される様子を見せる。

```text
ACTOR AGENT
Emma Carter
────────────────────────
14:03 AI → Manager

Production schedule change request:
Could Emma move Scene 42
to Wednesday 16:00–20:00?
────────────────────────
14:07 Manager → AI

She can make it after 4 PM,
but must finish by 8 PM.
────────────────────────
AI Interpretation

AVAILABLE
Window: 16:00–20:00
Constraint: Hard stop 20:00
```

### 9.6 Replanning 画面

全回答が揃った時点で Schedule Agent を起動する。

```text
ALL REQUIRED RESPONSES RECEIVED

Replanning production...
████████████████░░

Evaluating N schedule combinations

Checking:
✓ Cast
✓ Crew
✓ Equipment
✓ Location
✓ Continuity
✓ Budget
```

**実装要件:** 表示する組み合わせ数は固定のフェイク値にせず、小規模な Constraint Solver を実装して実際に候補評価を行う。実装コストは低く、システムの信頼性を大きく高める。

### 9.7 最終提案画面（Option 比較）

```text
AI REPLAN COMPLETE

3 FEASIBLE PLANS FOUND

OPTION A                    RECOMMENDED

Move Scene 42
Wed 16:00–20:00

Cost impact       +$8,400
Schedule delay     0 days
Risk               LOW

✓ Emma available
✓ Daniel available
✓ Alexa 35 available
✓ Studio B available
✓ Continuity valid

[ VIEW DETAILS ]
[ APPROVE PLAN ]
```

Option B / C も同様のカードで比較表示する。

### 9.8 Explainability（判断根拠の提示）

各 Option には必ず「Why?」を提示する。

```text
WHY OPTION A?

This option was selected because:
• Both principal actors are available
• No overtime is required
• Camera package can be extended
• Studio B is available
• Script continuity is preserved
• Production remains on schedule

Compared with Option B:
$21,400 lower cost
1 day less delay
```

### 9.9 Human Approval

**AIは勝手に確定してはならない。** 必ず人間（Producer）の承認を要求する。

```text
              AI RECOMMENDATION
                       ↓
                 Producer
                       ↓
            ┌──────────┴─────────┐
            ↓                    ↓
         APPROVE                REJECT
            ↓
      Execute changes
```

### 9.10 Execution 画面

Approve押下後の実行結果表示。ここでも MCP 呼び出しを可視化する。

```text
EXECUTING PLAN

✓ Actor booking updated
✓ Manager notified
✓ Equipment extended
✓ Studio B reserved
✓ Production calendar updated
✓ Call sheet regenerated
✓ Budget forecast updated
```

右側 MCP Activity:

```text
MCP ACTIVITY

actor.confirm_actor()
equipment.reserve()
location.confirm()
calendar.update()
budget.update()
```

### 9.11 Before / After サマリー画面

デモの締めくくり画面。

```text
INCIDENT RESOLVED

Detection → Resolution
2 min 47 sec

Resources coordinated
Actors             4
Crew               12
Equipment           8
Locations           2
Vendors             3

AI actions          37
MCP calls           52
Human decisions      1

Schedule delay
0 DAYS

Cost impact
+$8,400
```

---

## 10. プロモーション動画（Remotion）

ハッカソン提出物として、ライブデモに加えて **Remotion** で制作する短編プロモーション動画を用意する。審査員が事前資料として視聴する想定、および本番デモが失敗した場合のフォールバックとしても機能させる。

### 10.1 目的

- プロダクトのコンセプト（[1章](#1-プロダクトビジョン)）と価値提案を60〜90秒で伝える
- ライブデモが不安定な環境（回線・実演トラブル）でも訴求できる録画済み代替物を確保する
- SNS・提出フォーム等で使い回せる自己完結した動画アセットを作る

### 10.2 制作方式

- React コンポーネントとしてシーンを実装し、Remotion (`@remotion/cli`) でMP4にレンダリングする
- Dashboard・Agent Live View・MCP Activity Monitor・Resource Network View など、[9章](#9-ui仕様)の各UIコンポーネントを可能な限りそのまま流用し、実装とプロモーション動画のビジュアルを一致させる（別デザインを新規に作らない）
- ナレーション／字幕・BGMを合成し、単体で完結する動画として書き出す

### 10.3 構成案（60〜90秒）

[2.2 デモ時間構成](#22-デモ時間構成目安-約4分)を凝縮したダイジェスト版とする。

| 秒 | シーン |
| ---: | --- |
| 0:00 | プロダクトロゴ / コンセプトコピー表示 |
| 0:05 | Production Dashboard → Weather Alert 発生 |
| 0:15 | Multi-Agent 並行動作（Agent Live View） |
| 0:30 | MCP Activity Monitor / Resource Network View の伝播アニメーション |
| 0:45 | Manager 問い合わせ〜回答（External Communication Mock） |
| 0:55 | Replanning → Option A/B/C 提示 |
| 1:10 | Producer Approval → Execution |
| 1:20 | Incident Resolved サマリー + プロダクト名でクロージング |

### 10.4 実装優先順位への位置付け

プロモーション動画はUI実装（[9章](#9-ui仕様)）に依存するため、[13章 Phase 3](#phase-3ネットワーク可視化) 完了後、[Phase 4（仕上げ）](#phase-4仕上げ)の一部として制作する。UIコンポーネントの流用を前提とするため、UI実装より先行しては着手しない。

### 10.5 成果物

- MP4形式のプロモーション動画（1本、60〜90秒）
- Remotionプロジェクト一式（`remotion/` ディレクトリ想定、シーン単位でコンポーネント分割）

---

## 11. Mock と Real の境界

全てをMockにするのではなく、**「世界（外部リソース）はMockだが、それを操作するAIシステムは本物」**という構成を必須とする。デモ専用のフェイクアニメーションと誤解されないための最重要方針。

| Component | MVP 実装方針 |
| --- | --- |
| Gemini Orchestrator | **Real** |
| Agent reasoning | **Real** |
| MCP calls | **Real** |
| Resource data | Mock |
| Actor | Mock |
| Manager | Mock |
| Rental company | Mock |
| Location manager | Mock |
| Weather data | Mock / Real（切替可） |
| Scheduling（Constraint Solver） | **Real** |
| Dashboard | **Real** |
| Agent Event Stream | **Real** |

---

## 12. 技術構成

```text
Frontend
 └─ Next.js
     ├─ React
     ├─ Tailwind
     ├─ React Flow（Resource Network View 描画）
     └─ SSE / WebSocket（イベントストリーム受信）

Backend
 └─ Python / FastAPI

AI
 ├─ Gemini
 └─ Google ADK (Agent Development Kit)

Agent
 ├─ Production Orchestrator
 ├─ Actor Agent
 ├─ Equipment Agent
 ├─ Location Agent
 ├─ Schedule Agent
 └─ Budget Agent

MCP
 ├─ Actor MCP
 ├─ Equipment MCP
 ├─ Location MCP
 ├─ Script MCP
 ├─ Weather MCP
 └─ Budget MCP

Data
 ├─ SQLite / Firestore
 └─ Production Resource Graph

Google Cloud
 ├─ Cloud Run
 ├─ Gemini / Vertex AI
 └─ Firestore
```

---

## 13. 実装優先順位（フェーズ計画）

全Agentを初手から実装する必要はない。以下のフェーズで段階的に構築する。

### Phase 1（コア）
Production Dashboard → Weather incident → Orchestrator → Actor/Equipment/Location MCP → Replanning → Approval までの一連を完成させる。

### Phase 2（会話・可視化の追加）
Manager との Mock conversation、Agent Activity 表示、MCP Activity Monitor を追加する。

### Phase 3（ネットワーク可視化）
Resource Graph visualization、Option比較UI、Execution animation を追加する。

### Phase 4（仕上げ）
UI polish とデモシナリオの固定化・リハーサル。

---

## 14. 非機能要件

- **応答体験:** 全Agentの処理には意図的な遅延（[7章](#7-疑似遅延latency-simulation仕様)）を設け、Agenticな協調プロセスであることを体感させる。
- **説明可能性:** 全ての最終提案には判断根拠（Why?）を必ず添付する（[9.8](#98-explainability判断根拠の提示)）。
- **人間承認:** システムはいかなる変更も人間の承認なしに確定してはならない（[9.9](#99-human-approval)）。
- **アーキテクチャ制約:** UIからAgent/MCPへの直接呼び出しを禁止し、必ずOrchestrator経由とする（[3.2](#32-アーキテクチャ原則必須制約)）。
- **観測可能性:** 全Agentイベントを記録し、リアルタイムにDashboardへストリーミングできること（[8章](#8-イベントストリーム仕様)）。
- **置換可能性:** Mock MCP Serverは実サービスAPIへ置換可能なインターフェース設計とすること（[5章](#5-mcp-サーバー仕様)）。
- **提出物の冗長性:** ライブデモに加え、Remotion製プロモーション動画（[10章](#10-プロモーション動画remotion)）を提出物として用意し、実演トラブル時のフォールバックとする。

---

## 15. 成功基準（デモ評価軸）

以下を審査員が説明なしで理解できることを成功基準とする。

1. Geminiが中央のOrchestratorとして機能し、MCPを介して映画制作の人・モノ・場所にアクセスしている
2. 複数のAgentが並行して協調動作している（Multi-Agent Coordination）
3. 現実世界の変化（天候）を検知し、外部関係者との非構造化コミュニケーションをAIが構造化データへ変換している
4. AIが複数の代替案を評価し、根拠とともに提示している
5. 最終判断は人間（Producer）が行っている（Human-in-the-loop）
6. インシデント検知から解決までが閉ループとして完結している
