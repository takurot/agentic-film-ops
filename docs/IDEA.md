ハッカソン実装を前提に、**「実システムに見えること」「Agenticであることが審査員に一目で伝わること」「MCPが必然的に使われていること」**を重視した仕様にします。

# Agentic FilmOps

## Hackathon Demo System Specification v0.1

### 1. Product Vision

**Agentic FilmOps** は、映画制作に存在する人・機材・ロケーション・予算・脚本・外部環境をAIからアクセス可能な「Production Resource Network」として統合し、制作中の変更に対して複数AI Agentが協調して影響分析・問い合わせ・再計画を行うProduction Control Towerである。

中心となる価値提案は、

> **Every production resource becomes AI-accessible through MCP. When reality changes, agents coordinate the entire production in real time.**

単なる映画制作スケジューラーではなく、

**Observe → Reason → Coordinate → Re-plan → Human Approve → Execute**

までを閉ループ化する。

---

# 2. ハッカソンで見せるもの

MVPでは映画制作システム全体を作らない。

以下の1シナリオを完成度高くデモする。

### Demo Scenario

撮影前日、屋外Scene 42について豪雨予報が発生。

```text
Weather MCP
    ↓
Weather Agent
    ↓
Production Orchestrator
    ↓
影響分析
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
          Schedule Agent
                 ↓
          代替案 A / B / C
                 ↓
        Producer Dashboard
                 ↓
             APPROVE
                 ↓
         Production Update
```

この一連を**3〜5分のライブデモ**として成立させる。

---

# 3. システムアーキテクチャ

最重要部分。

```text
                    ┌───────────────────────┐
                    │  Producer Dashboard   │
                    │                       │
                    │ React / Next.js       │
                    └───────────┬───────────┘
                                │
                         WebSocket / API
                                │
                    ┌───────────▼───────────┐
                    │ PRODUCTION            │
                    │ ORCHESTRATOR          │
                    │                       │
                    │ Gemini                │
                    │ Agent Development Kit │
                    └───────────┬───────────┘
                                │
                           MCP Layer
                                │
        ┌──────────┬────────────┼────────────┬──────────┐
        │          │            │            │          │
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

**UIから各Agentを直接呼ばない。**

すべて、

```text
Dashboard
   ↓
Orchestrator
   ↓
MCP
   ↓
Resource / Agent
```

を通す。

これによって「全部のProduction ResourceがMCPでAIにつながっている」というコンセプトが明確になる。

---

# 4. Production Resource Graph

システムの中心データモデル。

### Scene

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

### Actor

```json
{
  "id": "ACT-001",
  "name": "Emma Carter",
  "manager": "MGR-001",
  "availability": [],
  "status": "confirmed"
}
```

### Equipment

```json
{
  "id": "EQ-001",
  "name": "ARRI Alexa 35",
  "vendor": "Cinema Rental Tokyo",
  "availability": [],
  "daily_cost": 1200
}
```

Graphとしては、

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

となる。

---

# 5. MCP Server構成

ハッカソンでは実サービスでなく**Mock MCP Server**でよい。

重要なのは「本物に置き換えられるInterface」になっていること。

### Actor MCP

Tools:

```text
get_actor()
get_actor_availability()
get_actor_constraints()

contact_manager()

get_contact_status()
get_manager_response()

hold_actor()
confirm_actor()
```

---

### Equipment MCP

```text
get_equipment()
check_availability()

request_extension()
request_reservation()

get_vendor_response()

reserve_equipment()
```

---

### Location MCP

```text
get_location()
check_availability()

contact_location_manager()

find_alternative_locations()

hold_location()
confirm_location()
```

---

### Weather MCP

```text
get_forecast()
get_weather_risk()
subscribe_weather_alert()
```

---

### Script MCP

```text
get_scene()
get_scene_requirements()

get_scene_dependencies()

get_continuity_constraints()
```

---

### Budget MCP

```text
get_current_budget()

estimate_change_cost()

calculate_overtime()

calculate_vendor_cost()
```

---

# 6. Agent構成

MCP ServerとAgentは分離する。

ここは審査員に説明できるようにしておく。

```text
Agent = Reasoning

MCP = Access / Action
```

### Production Orchestrator

システム全体の司令塔。

責務:

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

Geminiを使用。

---

### Actor Agent

役者関連の調整。

例えばOrchestratorから、

> Can Emma Carter move Scene 42 to Wednesday afternoon?

と依頼される。

Actor Agent:

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

---

# 7. Mockでも「待ち時間」を入れる

これは非常に重要。

全部が0.1秒で返ってくると、

**単なるAPI呼び出しに見える。**

意図的に、

```text
Actor Agent

Checking calendar...
      ↓ 1.2 sec

Checking contract...
      ↓ 0.8 sec

Contacting manager...
      ↓

WAITING FOR MANAGER

      ↓ 4 sec

Manager replied

"Emma can make it after 4 PM."

      ↓

Parsing response...

      ↓

AVAILABLE
```

とする。

Equipmentも、

```text
Checking inventory
       ↓
Contacting rental company
       ↓
WAITING
       ↓
Vendor confirmed
```

とする。

---

# 8. Event Stream

バックエンドでは全Agentイベントを記録する。

Event schema:

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

Status:

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

WebSocket/SSEでDashboardへ送信する。

これがUIのリアリティを作る。

---

# 9. Producer Dashboard

ここがデモの中心。

## Main Dashboard

```text
┌──────────────────────────────────────────────────────────────┐
│ AGENTIC FILMOPS                     PRODUCTION DAY 27 / 54   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ PRODUCTION HEALTH                                            │
│                                                              │
│ Schedule       Budget         Scenes        Risk             │
│   94%          $12.4M         82/143         MEDIUM           │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ 🔴 ACTIVE INCIDENT                                           │
│                                                              │
│ WEATHER RISK                                                 │
│                                                              │
│ Scene 42 — Rooftop Confrontation                             │
│ Tomorrow 14:00                                               │
│                                                              │
│ Heavy rain probability: 92%                                 │
│                                                              │
│  [ START AI IMPACT ANALYSIS ]                               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ TODAY                                                        │
│                                                              │
│ Scene 38 ██████ COMPLETED                                    │
│ Scene 39 ██████ COMPLETED                                    │
│ Scene 40 ██████ SHOOTING                                     │
└──────────────────────────────────────────────────────────────┘
```

---

# 10. Agent Live View

「START AI IMPACT ANALYSIS」を押した瞬間、

画面をAgent viewへ切り替える。

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

リアルタイムで変化する。

---

# 11. MCP Activity Monitor

今回のハッカソンでは、これをぜひ入れたいです。

画面右側に、

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

と表示。

これだけで、

> **「MCPで全部つながっている」**

ことを審査員が理解できる。

---

# 12. Resource Network View

さらに視覚的に、

```text
                       ORCHESTRATOR
                            │
                           MCP
                            │
       ┌────────────┬───────┼────────┬───────────┐
       ↓            ↓       ↓        ↓           ↓
     ACTORS      EQUIPMENT LOCATION SCRIPT     WEATHER
       ●            ●       ●        ●           ●
       │            │       │
    Managers      Vendor   Manager
```

と表示。

アクセス中のノードをアニメーションさせる。

例えば、

```text
ORCHESTRATOR
     │
     │ request
     ▼
 ACTOR MCP
     │
     ▼
 Emma
     │
     ▼
 Manager
```

の線が光る。

これは**デモ映えをかなり意識してよい部分**です。

---

# 13. External Communication Mock

役者マネージャーとのやり取りも画面に出す。

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

Window:
16:00–20:00

Constraint:
Hard stop 20:00
```

これで、

**LLMが非構造化コミュニケーションをProduction Dataへ変換している**

ことも示せる。

---

# 14. Replanning

全回答が揃ったらSchedule Agentを起動。

```text
ALL REQUIRED RESPONSES RECEIVED

Replanning production...

████████████████░░

Evaluating 28 schedule combinations

Checking:

✓ Cast
✓ Crew
✓ Equipment
✓ Location
✓ Continuity
✓ Budget
```

実際には28通り計算していなくても、デモ用Mockとして適当な数字を表示するのではなく、**小さなConstraint Solverを実装して本当に候補を評価**する方がよい。

これは実装コストが低い。

---

# 15. 最終提案画面

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

Option B/Cも比較できる。

---

# 16. Explainability

「Why?」を必ず入れる。

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

Agentが何を根拠に判断したかを見せる。

---

# 17. Human Approval

ここは重要。

AIが勝手に確定しない。

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

Approveを押す。

---

# 18. Execution

ここでもMCPを見せる。

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

右側では、

```text
MCP ACTIVITY

actor.confirm_actor()
equipment.reserve()
location.confirm()
calendar.update()
budget.update()
```

が流れる。

---

# 19. Before / After

最後の画面。

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

これでデモ終了。

---

# 20. デモの時間構成

理想は4分程度です。

|   時間 | デモ                   |
| ---: | -------------------- |
| 0:00 | Production Dashboard |
| 0:20 | Weather Alert        |
| 0:40 | Impact Analysis開始    |
| 1:00 | Multi-Agent動作        |
| 1:30 | MCPアクセス              |
| 1:50 | Manager問い合わせ         |
| 2:20 | 回答取得                 |
| 2:40 | Replanning           |
| 3:10 | Option A/B/C         |
| 3:30 | Producer Approval    |
| 3:45 | MCP Execution        |
| 4:00 | Incident Resolved    |

---

# 21. 技術構成

ハッカソンならこの程度が現実的です。

```text
Frontend
 └─ Next.js
     ├─ React
     ├─ Tailwind
     ├─ React Flow
     └─ SSE / WebSocket

Backend
 └─ Python / FastAPI

AI
 ├─ Gemini
 └─ Google ADK

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

# 22. Mockと本物の境界

全部Mockにしてしまうより、**Orchestratorだけは本当にGeminiに判断させる**ことを推奨します。

| Component           | MVP       |
| ------------------- | --------- |
| Gemini Orchestrator | **Real**  |
| Agent reasoning     | **Real**  |
| MCP calls           | **Real**  |
| Resource data       | Mock      |
| Actor               | Mock      |
| Manager             | Mock      |
| Rental company      | Mock      |
| Location manager    | Mock      |
| Weather data        | Mock/Real |
| Scheduling          | **Real**  |
| Dashboard           | **Real**  |
| Agent Event Stream  | **Real**  |

つまり、

**世界はMockだが、その世界を操作するAIシステムは本物**

にします。

これならデモ専用の「Fake Agent Animation」ではありません。

---

# 23. MVP実装優先順位

最初から全Agentを実装する必要はありません。

**Phase 1**

Production Dashboard → Weather incident → Orchestrator → Actor/Equipment/Location MCP → Replanning → Approvalまでを完成。

**Phase 2**

ManagerとのMock conversation、Agent Activity、MCP Activity Monitorを追加。

**Phase 3**

Resource Graph visualization、Option比較、Execution animationを追加。

**Phase 4**

UI polishとデモシナリオ固定化。

---

# 24. このシステムの最も重要な画面

個人的には、普通のDashboard以上に**「Production Network」画面を主役にした方が強い**と思います。

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

そして豪雨イベントが起きると、

**Scene 42 → Actor → Manager → Equipment → Vendor → Location**

とAgentのアクセスがリアルタイムにネットワーク上を伝播していく。

これを右側の

**Agent reasoning log + MCP call stream**

と同期させます。

そうすると審査員は説明を聞かなくても、

> 「Geminiが中央にいて、MCPを介して映画制作の人・モノ・場所すべてにアクセスし、現実世界とやり取りしながら再計画している」

と理解できます。

この**Production Network + Live Agent Activity + Human Approval**の3点をデモの中心に置くのが、このハッカソンでは特に強い構成だと思います。

