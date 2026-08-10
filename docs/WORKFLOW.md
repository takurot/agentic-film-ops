# Agentic FilmOps: Issue 実装ワークフロー

このドキュメントは、`docs/SPEC.md` とGitHub Issue（Milestone: `Phase 1.1〜1.5` / `Phase 2〜4`）で定義された各タスクを実装する際に、AIエージェントまたは開発者が従うべき実行手順書です。

本プロジェクトには `docs/PLAN.md` は存在しません。**タスクの一次情報は `docs/SPEC.md`（仕様）と GitHub Issue（実装タスク・Acceptance Criteria・Dependencies）** です。

---

## 1. 事前準備 (Context Setup)

### 1.0 入力パラメータ

このワークフローは以下のパラメータを受け取ります。

| パラメータ | 必須 | 例 | 説明 |
|-----------|------|-----|------|
| `ISSUE` | 必須 | `14` | 実装対象の GitHub Issue 番号 |

実装開始前に、Issue の内容を取得しコンテキストに取り込む:
```bash
gh issue view <ISSUE> --json title,body,comments,labels,milestone
```

### 1.1 依存 Issue の完了確認

各 Issue には多くの場合 `## Dependencies` セクション（`Depends on: #N` / `Blocks: #N`）が記載されている。**着手前に必ず確認する**:

```bash
gh issue view <ISSUE> --json body -q .body | grep -A5 "## Dependencies"
```

`Depends on:` に挙げられている Issue が Close されていない場合、原則として着手しない。順序を守らないとレイヤー間の前提（例: [5章 Transport & Invocation](../docs/SPEC.md#5-mcp-サーバー仕様) が未確定のまま個別MCPサーバーを実装する等）が崩れる。未クローズの依存がある場合はユーザーに報告し、指示を仰ぐ。

参考: Milestone は依存順に並んでいる。
```
Phase 1.1 Foundations
   ↓（直列・クリティカルパス）
Phase 1.2 MCP Servers  ─┐
Phase 1.3 Domain Agents ─┴─（ドメイン単位で並行可）
   ↓
Phase 1.4 Orchestration & Solver
   ↓
Phase 1.5 UI & Approval Loop
   ↓
Phase 2 → Phase 3（+ #36 プロモ動画素材録画）→ Phase 4（+ #28 プロモ動画仕上げ）
```

### 1.2 仕様確認

- **`docs/SPEC.md` の関連セクション**を熟読する。各 Issue 本文の `## Reference` に該当章番号が明記されている。
- Issue 本文の `## Scope` / `## Acceptance Criteria` を実装のゴールとして固定する。
- [3.2 アーキテクチャ原則](../docs/SPEC.md#32-アーキテクチャ原則必須制約)（UIはAgentを直接呼ばない、必ずOrchestrator経由）など、**プロジェクト全体を横断する制約**は担当Issueの種類に関わらず常に確認する。

### 1.3 ブランチ作成

```bash
git checkout main
git pull
git checkout -b issue/<ISSUE>-description
```

---

## 2. 実装プランニング (Implementation Planning)

実装に入る前に実装計画を立案する。コーディングを始めるのはプランが確定してから。

> **注意**: `EnterPlanMode` / `ExitPlanMode` はユーザーに承認を求める対話的なツールであり、本ワークフロー（自律実行）では使用しない。代わりに、エージェント自身でドラフトプランを作成し、サブエージェントによる多角的レビューを経てプランをブラッシュアップ・確定する。

### 2.1 ドラフトプランの作成

以下のコンテキストをもとにドラフトプランを作成する:
- Issue の `## Scope` / `## Acceptance Criteria` / `## Dependencies`
- `docs/SPEC.md` の該当セクション（Issue の `## Reference` に記載）
- 依存Issue（Close済み）の実装内容・インターフェース

### 2.2 プランに含めるべき項目

| 項目 | 内容 |
|------|------|
| **変更対象ファイル** | 新規作成・修正するファイル一覧（`backend/`, `frontend/`, `remotion/` 等） |
| **実装ステップ** | 順序付きのタスク分解（依存関係を考慮） |
| **テスト戦略** | Unit / Integration / E2E の対象と配置（[3節](#3-実装サイクル-tdd)参照） |
| **依存・リスク** | 外部ライブラリ、[3.2 アーキテクチャ制約](../docs/SPEC.md#32-アーキテクチャ原則必須制約)への抵触有無、breaking changeの有無 |
| **Acceptance Criteria の対応** | Issue の各 Acceptance Criteria をどの実装・テストが担保するか |

### 2.3 サブエージェントによる多角的レビュー

ドラフトプランができたら、`Agent` ツールを使って以下の観点から**並列に**レビューを依頼し、プランをブラッシュアップする（1メッセージで複数の `Agent` 呼び出しを行う）。各エージェントには、ドラフトプラン全文・Issue本文・関連する `docs/SPEC.md` セクションを渡す。

| レビュー観点 | 推奨サブエージェント | チェック内容 |
|---|---|---|
| 仕様・Acceptance Criteria 整合性 | `architect` または `planner` | `docs/SPEC.md` との整合、ステップ分解の妥当性、Acceptance Criteria の網羅性 |
| テスト戦略 | `tdd-guide` | Unit / Integration / E2E の配置・粒度、80%カバレッジ目標の達成可否 |
| アーキテクチャ制約 | `architect` | [3.2](../docs/SPEC.md#32-アーキテクチャ原則必須制約)（UI→Orchestrator→MCP以外の直接呼び出し禁止）、[5章 Transport & Invocation](../docs/SPEC.md#5-mcp-サーバー仕様)（MCP共通基盤への準拠）への抵触有無 |
| セキュリティ | `security-reviewer` | Gemini API キー等のシークレット管理、MCP経由の入力検証、Mock↔Real境界（[11章](../docs/SPEC.md#11-mock-と-real-の境界)）を越える実装がないか |
| 言語別コーディング規約 | `python-reviewer`（backend） / `typescript-reviewer`（frontend） | 対象言語の慣用パターン・型安全性 |

レビュー結果から P1（重大）/ P2（重要）相当の指摘をドラフトプランに反映する。指摘が解消されるまで（目安1〜2回）このサイクルを繰り返す。タスクが小規模で上記観点の一部が明らかに無関係な場合は、該当観点のレビューを省略してよい。

2回のサイクルを経ても解消できない P1 指摘が残る場合は、その時点のドラフトプランと未解決の指摘内容をユーザに報告し、指示を仰ぐ。

### 2.4 プラン確定

以下をすべて満たしたらプランを確定し、**ユーザーへの承認を求めずに**そのままセクション 3（実装サイクル）へ進む:

- [ ] 実装ステップが具体的なファイル名・関数名レベルまで落とされている
- [ ] テストケースの雛形が明確になっている
- [ ] Issue の Acceptance Criteria との対応が取れている
- [ ] サブエージェントレビューの P1/P2 指摘が解消されている
- [ ] 不明点・前提条件の曖昧さがない（あれば `docs/SPEC.md`・依存Issue・既存コードを調査して解消する。それでも解決不能な場合のみユーザーに報告する）

---

## 3. 実装サイクル (TDD)

**厳格な TDD (Test-Driven Development)** サイクルを守って実装を進める。対象コンポーネントに応じてツールチェーンを使い分ける。

| コンポーネント | 言語/フレームワーク | テストランナー |
|---|---|---|
| Backend（FastAPI, Agent, MCP Server） | Python | `pytest` (+ `pytest-cov`) |
| Frontend（Dashboard, Agent Live View 等） | TypeScript / React (Next.js) | `vitest` または `jest` + Testing Library |
| E2E（デモシナリオ通し） | Playwright | `/e2e` Skill |

> **Skills の活用**: 実装・テスト・レビューの各フェーズで、タスクに適した Skills（`/tdd`, `/python-review`, `/e2e`, `/code-review` など）を積極的に使うこと。汎用的な実装より Skill を使った方が品質・速度ともに高い。

1. **Red（テスト作成）**:
   - Issue の `## Acceptance Criteria` に基づき、失敗するテストケースを作成する。
   - `pytest` / `vitest` を実行し、**期待通りに失敗すること**を確認する。
2. **Green（最小実装）**:
   - テストをパスさせるための最小限の実装を行う。
   - `pytest` / `vitest` を再実行し、パスすることを確認する。
3. **Refactor（リファクタリング）**:
   - コードの可読性、構造、パフォーマンスを改善する。
   - 再度テストを実行し、破壊していないことを確認する。

---

## 4. 品質保証 (Quality Assurance)

実装完了後、PR作成前に以下のローカル検証を**必ず**実行する。

### 4.1 テスト全実行

```bash
# Backend
cd backend && pytest --cov

# Frontend
cd frontend && npm test

# E2E（対象範囲がある場合）
Skill("e2e")
```

- カバレッジ目標: 80%以上（`~/.claude/rules/common/testing.md` 準拠）

### 4.2 静的解析 (Lint & Format)

```bash
# Backend
ruff check backend/ && ruff format --check backend/

# Frontend
cd frontend && npm run lint
```

- 警告はすべて修正する。

### 4.3 プロジェクト固有の検証チェックリスト

`docs/SPEC.md` [14章 非機能要件](../docs/SPEC.md#14-非機能要件)に基づく、このプロジェクト特有の検証項目。実装内容に該当する項目のみ確認する。

- [ ] UI から Agent / MCP を直接呼んでいないか（必ず Orchestrator 経由。[3.2](../docs/SPEC.md#32-アーキテクチャ原則必須制約)）
- [ ] Human Approval なしに Production 状態が変更されていないか（[9.9](../docs/SPEC.md#99-human-approval)）
- [ ] Agent イベントが [8.1 スキーマ](../docs/SPEC.md#81-イベントスキーマ)に準拠しているか
- [ ] Mock MCP のツールシグネチャ・戻り値が本番想定のまま固定されているか（[5章](../docs/SPEC.md#5-mcp-サーバー仕様)）
- [ ] 疑似遅延（[7章](../docs/SPEC.md#7-疑似遅延latency-simulation仕様)）が設定可能な形で実装されているか。Gemini呼び出しを含む場合、疑似遅延が実レイテンシへの**加算**ではなく**下限**として実装されているか
- [ ] Before/After Summary 等の数値をハードコードしていないか（実測値から算出、[9.11](../docs/SPEC.md#911-before--after-サマリー画面)）

---

## 5. コードレビュー → QA ゲート

ローカル検証が通った後、コミット前に Skill によるレビュー→QAを行う。ここで見つかった問題は修正し、該当テストを追加または更新してから、再度 [4. 品質保証](#4-品質保証-quality-assurance) へ戻る。

### 5.1 コードレビュー

```
Skill("code-review")
```

- 重点観点:
  - `docs/SPEC.md` / Issue の Acceptance Criteria とのズレ
  - [3.2 アーキテクチャ制約](../docs/SPEC.md#32-アーキテクチャ原則必須制約)（UI→Orchestrator→MCPの経路遵守）の崩れ
  - シークレット・認証情報の扱い（`security-review` Skillも併用）
  - テスト不足、回帰リスク
  - 不要な scope creep や関連しない変更
- P1/P2 相当の指摘は必ず修正する。修正後は関連テストを再実行し、必要なら `Skill("code-review")` を再実行する。

> **`code-review ultra`（マルチエージェントのクラウドレビュー）について**: これはユーザートリガー専用のコマンドであり、AIエージェントが自律的に起動することはできない（課金を伴うため）。自律実行フローでは通常の `Skill("code-review")` を用いる。ユーザーがより厳密なレビューを希望する場合は、その旨をユーザーに提案するに留める。

### 5.2 QA

実装対象に応じて動作確認を行う。

- **Backend / MCP Server**: `uvicorn` でローカル起動し、対象エンドポイント・MCPツールを実際に呼び出して応答を確認する。Weather MCP等は疑似遅延・mock応答の内容も確認する。
- **Frontend**: `npm run dev` で起動し、対象UI画面を操作する。表示崩れ、コンソールエラー、ネットワークエラーがないか確認する（`mcp__claude-in-chrome__*` ツールでのブラウザ確認も活用可）。
- **Agent / Orchestrator**: Event Stream の出力を実際に確認し、[8.2 ステータス種別](../docs/SPEC.md#82-ステータス種別)の遷移が仕様通りか確認する。
- **backend-only / schema-only の変更**: contract test、negative test、スキーマ互換性の確認を優先する（runnable なUIがない場合）。

QA でバグを見つけた場合:
1. 最小修正を行う。
2. 再現テストまたは回帰テストを追加する。
3. `pytest` / `vitest` / lint を再実行する。
4. `Skill("code-review")` を再実行し、未解決の重大指摘がないことを確認する。

### 5.3 記録

PR本文に以下を記録する:
- `code-review` の結果概要と未解決事項の有無
- QAの対象・実行観点・結果
- 修正した指摘と、それを担保するテスト

---

## 6. ドキュメント更新

コード以外の成果物を同期する。

- **Issue更新**: 完了した Acceptance Criteria のチェックボックスを更新（PR本文でも `Closes #<ISSUE>` により自動連動）。
- **`docs/SPEC.md` 更新**: 実装中に仕様の微修正が必要になった場合、反映する。章番号・アンカーの整合を崩さないよう注意する。
- **`README.md` 更新**: 必要に応じて更新する（英語で記述されているため、英語で追記する）。

---

## 7. PR作成と最終確認 (Finalization)

全てのチェックが完了したら、変更をプッシュしPRを作成する。

1. **Commit**:
   - コミットメッセージは Conventional Commits に従う（`feat:`, `fix:`, `refactor:`, `test:`, `docs:` 等）。
   - 例: `feat(backend): implement Weather MCP mock server (#3)`
   - 新規ファイル追加時は必ず `git add <file>` を忘れないこと。
   - コミットメッセージ末尾に `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` を付与する（本リポジトリの既存コミット慣習に合わせる）。
2. **Push**:
   ```bash
   git push origin issue/<ISSUE>-description
   ```
3. **PR 作成**:
   - タイトル: `[#<ISSUE>] 実装の概要`
   - 本文:
     - `Closes #<ISSUE>`
     - Issue の Acceptance Criteria 達成状況
     - 実施したテスト結果
     - `code-review` / QA の実行結果と、未解決事項がないこと
4. **CI 確認**（CIが設定されている場合）:
   - GitHub Actions のステータスを監視し、失敗した場合は即座に修正コミットを追加する。

---

## 8. セカンドオピニオンレビュー (任意)

実装内容が複雑、またはレビューで判断に迷う指摘が残った場合、`codex:rescue` サブエージェントに調査・二次意見を依頼できる。

```
Skill("codex:rescue")
```

- 用途: 行き詰まった実装の診断、独立した視点でのコードレビュー、difficult なバグの根本原因調査。
- 必須ステップではない。5.1のコードレビューで十分な場合はスキップしてよい。

---

## 9. マージ判定 (Merge Gate)

以下の全条件を満たしたときのみマージを実行する。

- [ ] `code-review` の P1/P2 指摘がすべて対処済み
- [ ] 全テスト（Unit / Integration / E2E）がパス
- [ ] CI（設定されている場合）の全ジョブがオールグリーン
- [ ] QA で未解決の重大指摘なし
- [ ] Issue の Acceptance Criteria をすべて達成

全条件を満たした場合:
```bash
gh pr merge <PR番号> --squash --delete-branch
```

---

## 10. セッション学習の保存 (Post-merge Learning)

マージ完了後、セッションで得た再利用可能な知見を `/learn` スキルで自動保存する。

### 10.1 非インタラクティブ実行

`/learn` をそのまま呼ぶとユーザー確認を求めるインタラクティブモードになる。エージェントからは **`--auto` 引数を渡して確認ステップをスキップ**する:

```
Skill("learn", args="--auto")
```

### 10.2 抽出対象の優先順位

このセッションで以下が発生していた場合に限り保存する（トリビアルな修正は除外）:

1. **エラー解決パターン** — ビルドエラー、テスト失敗、CI失敗の根本原因と修正方法
2. **MCP / Agent 実装固有の挙動** — `mcp` SDK, Gemini/ADK, FastAPI の非自明な挙動
3. **ワークアラウンド** — ライブラリのバグ、API制限、バージョン固有の問題
4. **プロジェクト固有パターン** — [3.2 アーキテクチャ制約](../docs/SPEC.md#32-アーキテクチャ原則必須制約)を守るための実装パターン、Mock/Real境界の扱い方

### 10.3 保存先と MEMORY.md 更新

`/learn --auto` の実行後、保存されたファイルを確認し、`MEMORY.md` のインデックスに1行追加する。

---

## 補足: 本ワークフローとタスク管理の関係

このプロジェクトは `docs/PLAN.md` を持たず、代わりに **GitHub Issue + Milestone** がタスクバックログとして機能する。

- Issue本文の `## Scope` / `## Acceptance Criteria` が旧来の PLAN.md の「実装タスク」「Exit Criteria」に相当する。
- Issue本文の `## Dependencies` が実装順序の制約を表す（[1.1節](#11-依存-issue-の完了確認)参照）。
- Milestone（`Phase 1.1`〜`Phase 1.5`, `Phase 2`〜`Phase 4`）が `docs/SPEC.md` [13章 実装優先順位](../docs/SPEC.md#13-実装優先順位フェーズ計画)に対応する。

新しい作業単位を追加する場合は、Issueとして起票し、該当する `docs/SPEC.md` の章を `## Reference` に明記し、依存関係を `## Dependencies` に明記すること。

---

**Note to AI Agent**: このワークフローに従ってタスクを実行する際は、**「Issue取得 → 依存Issueの完了確認 → ブランチ作成 → ドラフトプラン作成 → サブエージェントによる多角的レビューでプランをブラッシュアップ・確定 → TDD実装（適切なSkills使用）→ Lint/Format → プロジェクト固有チェックリスト → code-review → QA → 必要な修正 → Commit → Push → PR作成（`Closes #<ISSUE>` を含む）→ （必要なら codex:rescue でセカンドオピニオン）→ CI確認 → マージ → `Skill("learn", args="--auto")` でセッション学習を保存」までの工程を自律的に（ユーザ承認を挟まずに）実行すること**。
解決不能なエラーが発生した場合、未クローズの依存Issueがある場合、または P1 指摘が対処不能な場合のみユーザに報告し、指示を仰ぐこと。
