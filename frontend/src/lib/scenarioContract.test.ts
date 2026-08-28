import { describe, it, expect } from "vitest";
import { getDemoScenario, canonicalScenario } from "./scenarioLoader";
import { MOCK_HEALTH, MOCK_INCIDENTS, MOCK_ANALYSIS, MOCK_EXECUTION } from "./mockData";

describe("Scenario Contract & Multi-surface Parity", () => {
  it("loads the canonical demo scenario with valid structure", () => {
    const scenario = getDemoScenario();
    expect(scenario.meta.scenario_id).toBe("SCENARIO-SC042-RAIN-V1");
    expect(scenario.meta.version).toBe("1.0.0");
    expect(scenario.production.production_day_current).toBe(27);
    expect(scenario.production.production_day_total).toBe(54);
    expect(scenario.production.budget_spent_usd).toBe(12400000);
    expect(scenario.production.budget_total_usd).toBe(20000000);
  });

  it("ensures frontend mock fixtures match canonical scenario", () => {
    expect(MOCK_HEALTH.production_day_current).toBe(canonicalScenario.production.production_day_current);
    expect(MOCK_HEALTH.production_day_total).toBe(canonicalScenario.production.production_day_total);
    expect(MOCK_HEALTH.budget_total_usd).toBe(canonicalScenario.production.budget_total_usd);
    expect(MOCK_HEALTH.budget_spent_usd).toBe(canonicalScenario.production.budget_spent_usd);

    expect(MOCK_INCIDENTS[0].incident_id).toBe(canonicalScenario.incident.incident_id);
    expect(MOCK_INCIDENTS[0].scene_id).toBe(canonicalScenario.incident.scene_id);

    expect(MOCK_ANALYSIS.options.length).toBe(canonicalScenario.options.length);
    expect(MOCK_ANALYSIS.options[0].option_id).toBe("OPT-A");
    expect(MOCK_ANALYSIS.options[0].cost_impact).toBe(4200);

    expect(MOCK_EXECUTION.steps).toEqual(canonicalScenario.execution.steps);
  });

  it("verifies mathematical consistency for avoided cost", () => {
    const model = canonicalScenario.cost_benefit_model;
    expect(model.standby_day_penalty_usd).toBe(84000);
    expect(model.option_a_variance_usd).toBe(4200);
    expect(model.net_cost_avoided_usd).toBe(79800);
    expect(model.standby_day_penalty_usd - model.option_a_variance_usd).toBe(model.net_cost_avoided_usd);
  });

  it("validates referential integrity of resource IDs", () => {
    const actors = (canonicalScenario.resources as { actors: Array<{ id: string }> }).actors.map((a) => a.id);
    const locations = (canonicalScenario.resources as { locations: Array<{ id: string }> }).locations.map((l) => l.id);
    const equipment = (canonicalScenario.resources as { equipment: Array<{ id: string }> }).equipment.map((e) => e.id);

    expect(actors).toContain("ACT-001");
    expect(actors).toContain("ACT-002");
    expect(locations).toContain("LOC-003");
    expect(locations).toContain("LOC-STUDIO-B");
    expect(equipment).toContain("EQ-001");
    expect(equipment).toContain("EQ-004");
  });
});
