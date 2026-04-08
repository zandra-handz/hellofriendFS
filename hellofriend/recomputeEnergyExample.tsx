/**
 * Client-side mirror of GeckoScoreState.recompute_energy (users/models.py:445).
 *
 * Call `recomputeEnergy` every frame/second with the latest local
 * accumulations.  Every 60 s the backend sync overwrites `snapshot`
 * with the authoritative values, resetting drift.
 */

// ── constants (users/constants.py) ──────────────────────────────
const STEPS_TO_FULL_DRAIN = 100_000;
const STEP_FATIGUE_PER_STEP = 1.0 / STEPS_TO_FULL_DRAIN;
const STREAK_FATIGUE_MULTIPLIER = 0.25;
const SURPLUS_CAP = 2.0;

// ── types ───────────────────────────────────────────────────────

/** Snapshot from the GeckoScoreState serializer (last backend sync). */
export interface EnergySnapshot {
  energy: number;
  surplusEnergy: number;
  /** ISO-8601 string — last time backend computed energy. */
  energyUpdatedAt: string;
  /** ISO-8601 string | null */
  revivesAt: string | null;

  multiplier: number;
  baseMultiplier: number;
  /** ISO-8601 string — when streak expires. */
  expiresAt: string;

  rechargePerSecond: number;
  streakRechargePerSecond: number;

  /** From GeckoConfigs. Default 1.0. */
  stamina: number;
  /** From GeckoConfigs. Default 60. */
  revivalSeconds: number;
}

/** What the frontend is accumulating locally between syncs. */
export interface LocalAccumulation {
  /** Total steps taken since last sync. */
  steps: number;
  /** Total active seconds in the current session since last sync. */
  activeSeconds: number;
}

export interface EnergyResult {
  energy: number;
  surplusEnergy: number;
  revivesAt: string | null;
}

// ── computation ─────────────────────────────────────────────────

export function recomputeEnergy(
  snapshot: EnergySnapshot,
  local: LocalAccumulation,
  nowMs: number = Date.now(),
): EnergyResult {
  const energyUpdatedAtMs = new Date(snapshot.energyUpdatedAt).getTime();
  const elapsed = (nowMs - energyUpdatedAtMs) / 1000;

  let energy = snapshot.energy;
  let surplusEnergy = snapshot.surplusEnergy;
  let revivesAt = snapshot.revivesAt;

  if (elapsed <= 0) {
    return { energy, surplusEnergy, revivesAt };
  }

  // ── dead: waiting for revival ─────────────────────────────────
  if (energy <= 0 && surplusEnergy <= 0) {
    if (revivesAt && nowMs >= new Date(revivesAt).getTime()) {
      return { energy: 0.05, surplusEnergy: 0, revivesAt: null };
    }
    if (!revivesAt) {
      const reviveTime = new Date(energyUpdatedAtMs + snapshot.revivalSeconds * 1000);
      return { energy: 0, surplusEnergy: 0, revivesAt: reviveTime.toISOString() };
    }
    return { energy: 0, surplusEnergy: 0, revivesAt };
  }

  // ── active computation ────────────────────────────────────────
  const { steps: newSteps, activeSeconds } = local;
  const restSeconds = Math.max(0, elapsed - activeSeconds);

  const streakIsActive =
    snapshot.multiplier > snapshot.baseMultiplier &&
    new Date(snapshot.expiresAt).getTime() > energyUpdatedAtMs;

  let fatigue: number;
  let recharge: number;

  if (streakIsActive && activeSeconds > 0) {
    const streakEndMs = Math.min(
      new Date(snapshot.expiresAt).getTime(),
      nowMs,
    );
    const streakSeconds = Math.max(
      0,
      (streakEndMs - energyUpdatedAtMs) / 1000,
    );
    const streakRatio = Math.min(1.0, streakSeconds / elapsed);

    const streakActiveSeconds = activeSeconds * streakRatio;
    const streakSteps = newSteps * (streakActiveSeconds / activeSeconds);
    const normalSteps = newSteps - streakSteps;

    fatigue =
      normalSteps * STEP_FATIGUE_PER_STEP +
      streakSteps * STEP_FATIGUE_PER_STEP * STREAK_FATIGUE_MULTIPLIER;

    recharge =
      restSeconds * snapshot.rechargePerSecond +
      streakActiveSeconds * snapshot.streakRechargePerSecond;
  } else {
    fatigue = newSteps * STEP_FATIGUE_PER_STEP;
    recharge = restSeconds * snapshot.rechargePerSecond;
  }

  const effectiveRecharge = recharge * snapshot.stamina;
  const effectiveFatigue = fatigue / snapshot.stamina;
  const net = effectiveRecharge - effectiveFatigue;

  // ── apply net to energy / surplus ─────────────────────────────
  if (net >= 0) {
    const roomInMain = 1.0 - energy;
    if (net <= roomInMain) {
      energy += net;
    } else {
      energy = 1.0;
      surplusEnergy = Math.min(SURPLUS_CAP, surplusEnergy + (net - roomInMain));
    }
  } else {
    let drain = -net;
    if (surplusEnergy >= drain) {
      surplusEnergy -= drain;
    } else {
      drain -= surplusEnergy;
      surplusEnergy = 0;
      energy = Math.max(0, energy - drain);
    }
  }

  // ── revival bookkeeping ───────────────────────────────────────
  if (energy <= 0 && surplusEnergy <= 0) {
    if (!revivesAt) {
      const reviveTime = new Date(nowMs + snapshot.revivalSeconds * 1000);
      revivesAt = reviveTime.toISOString();
    }
  } else {
    revivesAt = null;
  }

  return { energy, surplusEnergy, revivesAt };
}
