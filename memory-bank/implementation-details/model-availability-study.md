# Model and Provider Availability Study

*Design status: planning*  
*Created: 2026-08-15 01:32:26 IST*  
*Related task: T11*

## Purpose

Measure availability and performance as a function of provider, model, harness condition, and time of day. The design is deliberately provider- and model-agnostic so Kimi is one configuration, not a special case.

OpenClaw is expected to remain available with an OpenAI main agent. The experiment tests whether selected provider/model calls work; the OpenAI agent may later analyse the data but must not be in the direct measurement request path.

## Experimental conditions

Each observation has two independent dimensions:

| Dimension | Examples | Meaning |
|---|---|---|
| Provider/model target | `provider-a/model-x`, `provider-b/model-y` | The service and exact model being tested |
| Harness mode | `direct`, `openclaw` | Direct provider HTTPS request versus an OpenClaw-mediated request |

The `direct` mode is the primary outage measurement. The optional `openclaw` mode measures the end-to-end user path and must not replace or silently retry a failed direct request. Results from the two modes are never pooled without an explicit mode term in analysis.

## Measurement plane

```text
OS scheduler ──> standalone probe ──> provider adapter ──> provider API
                       │
                       └──────────────> append-only JSONL
```

The standalone probe uses ordinary HTTPS and local libraries only. It does not call OpenClaw, an agent, a session, a tool, Telegram, or an OpenAI fallback. Configuration errors and transport failures are recorded as events rather than repaired by another model.

The OpenClaw mode, if enabled, is a separate job using the same event schema. It may use an OpenClaw cron `agentTurn`, but it must have silent delivery and must write its result to the local JSONL sink. It should not send a Telegram message per call.

## JSONL event contract

One line is written for every scheduled attempt, including configuration, timeout, rate-limit, and transport failures. Do not write secrets, prompts containing private data, response bodies, or credentials.

```json
{
  "schema_version": 1,
  "event_type": "model_probe",
  "attempt_id": "uuid",
  "scheduled_at": "2026-08-15T01:30:00+05:30",
  "started_at": "2026-08-14T20:00:01Z",
  "finished_at": "2026-08-14T20:00:08Z",
  "timezone": "Asia/Kolkata",
  "provider": "provider-a",
  "model": "model-x",
  "harness": "direct",
  "probe_profile": "small-fixed-prompt-v1",
  "outcome": "success",
  "failure_class": null,
  "http_status": 200,
  "latency_ms": 7021,
  "time_to_first_token_ms": null,
  "input_tokens": null,
  "output_tokens": null,
  "retry_count": 0,
  "scheduler_job": "availability-probe-direct",
  "host_class": "local",
  "maintenance_skipped": false
}
```

Recommended `outcome` values are `success`, `failure`, `skipped`, and `configuration_error`. Recommended `failure_class` values are `timeout`, `dns`, `connect`, `tls`, `http_4xx`, `http_5xx`, `rate_limit`, `empty_response`, `invalid_response`, `local_resource`, and `unknown`. HTTP status and provider error codes may be recorded when non-sensitive.

The first attempt is the primary observation. Retries, if permitted for diagnostics, must be separate fields or separate events and must never turn a failed first attempt into a success.

## Scheduling design

### Silent measurement jobs

- Direct probe: ordinary OS cron/launchd/systemd timer; no OpenClaw dependency.
- Optional OpenClaw probe: OpenClaw cron job with silent/no-reply delivery; no Telegram notification.
- Each invocation uses a balanced or deterministic-randomized model order.
- A lock prevents overlapping batches.
- The maintenance flag is checked before network activity, following `cron-management`.
- Job names should be descriptive, for example `availability-probe-direct` and `availability-probe-openclaw`, so `cronctl` can list, pause, resume, and inspect them.

### Reporting jobs

Separate aggregate jobs may notify the user:

- `availability-report-hourly`: summarize the immediately preceding one-hour window.
- `availability-report-4h`: summarize the immediately preceding four-hour window.

Each report should include attempts, first-attempt successes, failures by class, success rate, timeout/rate-limit rates, latency quantiles where available, and missing expected probes. It should identify provider, model, and harness separately. A report with no observations should say so rather than imply success.

Reporting may be an OpenClaw cron using the OpenAI main agent, but it must read only the local JSONL/derived data and must not re-run probes. Delivery is allowed only for these aggregate jobs; measurement jobs use no Telegram delivery.

## Cron-control compatibility

All jobs must follow the existing `cron-management` contract:

1. Check `/tmp/cron-paused` before network calls.
2. Append a local skipped event when maintenance mode is active.
3. Use stable descriptive names compatible with `cronctl` fuzzy matching.
4. Keep direct OS jobs independent of OpenClaw so they continue to observe provider failures when the harness is unavailable.
5. Treat `cronctl maintenance on` as a global emergency stop for jobs that implement the check.

The direct OS scheduler is not itself managed by `openclaw cron`; its installation and pause/resume mechanism must be documented alongside the job. OpenClaw report jobs can be managed by `cronctl` normally.

## Analysis plan

Primary response: first-attempt failure probability by provider/model/harness and time bin. Keep rate limits separate from service outages. Include date, weekday, probe profile, and network-control observations as covariates. Report confidence intervals and sample counts; do not label sparse bins as findings. Analyse declared incidents separately rather than silently excluding them.

## Decisions still required

- Provider endpoint/adapters and exact model IDs.
- Direct versus OpenClaw harness profiles to enable.
- Probe interval and per-provider request budget.
- Prompt/profile and timeout.
- JSONL location and retention policy.
- Whether the hourly and four-hourly reports should be OpenClaw cron jobs or standalone notification scripts.
- Whether OS-level direct jobs should be included in the existing cron-control maintenance flag by default.
