-- Smart DevOps Assistant Supabase PostgreSQL schema + RBAC seed data
-- Run in Supabase SQL Editor for a fresh development database.
-- WARNING: This script drops/recreates the app tables listed below.

create extension if not exists pgcrypto;

begin;

drop table if exists executions cascade;
drop table if exists approval_requests cascade;
drop table if exists chat_messages cascade;
drop table if exists user_sessions cascade;
drop table if exists users cascade;

create table users (
  id varchar(36) primary key default gen_random_uuid()::text,
  email varchar(255) not null unique,
  username varchar(50) not null unique,
  hashed_password varchar(255) not null,
  role varchar(20) not null default 'developer' check (role in ('admin','operator','developer','viewer')),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index ix_users_email on users(email);
create index ix_users_username on users(username);
create index ix_users_role on users(role);

create table user_sessions (
  id varchar(36) primary key default gen_random_uuid()::text,
  user_id varchar(36) not null references users(id) on delete cascade,
  refresh_token varchar(512) not null unique,
  expires_at timestamptz not null,
  is_revoked boolean not null default false,
  ip_address varchar(100),
  user_agent varchar(255),
  created_at timestamptz not null default now()
);

create index ix_user_sessions_refresh_token on user_sessions(refresh_token);
create index ix_user_sessions_user_id on user_sessions(user_id);

create table chat_messages (
  id serial primary key,
  session_id varchar(128) not null,
  role varchar(10) not null check (role in ('human','ai')),
  content text not null,
  created_at timestamptz not null default now()
);

create index ix_chat_messages_session_id on chat_messages(session_id);
create index ix_chat_messages_created_at on chat_messages(created_at);

create table approval_requests (
  id varchar(36) primary key default gen_random_uuid()::text,
  session_id varchar(128),
  requested_by varchar(100) not null,
  tool_name varchar(100),
  tool_input text,
  action text not null,
  risk_level varchar(20) not null check (risk_level in ('low','medium','high','critical')),
  summary text not null,
  status varchar(20) not null default 'pending' check (status in ('pending','approved','rejected','expired','timed_out')),
  payload text,
  decided_by varchar(100),
  decision_note text,
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  expires_at timestamptz
);

create index ix_approval_requests_session_id on approval_requests(session_id);
create index ix_approval_requests_status on approval_requests(status);
create index ix_approval_requests_created_at on approval_requests(created_at);

create table executions (
  id varchar(36) primary key default gen_random_uuid()::text,
  session_id varchar(128),
  requested_by varchar(100) not null,
  tool_name varchar(100),
  tool_input text,
  status varchar(20) not null default 'pending' check (status in ('pending','running','completed','failed','cancelled')),
  summary text not null,
  details text,
  source varchar(50),
  approval_id varchar(36) references approval_requests(id) on delete set null,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index ix_executions_session_id on executions(session_id);
create index ix_executions_requested_by on executions(requested_by);
create index ix_executions_status on executions(status);
create index ix_executions_started_at on executions(started_at);

insert into users (email, username, hashed_password, role, is_active, created_at) values
  ('admin@example.com', 'admin', crypt('admin123', gen_salt('bf', 12)), 'admin', true, now() - interval '12 days'),
  ('operator@devops.local', 'operator', crypt('operator123', gen_salt('bf', 12)), 'operator', true, now() - interval '10 days'),
  ('devops.engineer@example.com', 'devops.engineer', crypt('developer123', gen_salt('bf', 12)), 'developer', true, now() - interval '9 days'),
  ('viewer@company.local', 'viewer', crypt('viewer123', gen_salt('bf', 12)), 'viewer', true, now() - interval '8 days');

insert into chat_messages (session_id, role, content, created_at) values
  ('demo-admin-session', 'human', 'Show me pending approval requests and recent failed executions.', now() - interval '2 hours'),
  ('demo-admin-session', 'ai', 'I found two pending approval requests and one failed execution in the last 24 hours. The highest risk item is a production workflow dispatch requiring operator/admin approval.', now() - interval '2 hours' + interval '15 seconds'),
  ('demo-operator-session', 'human', 'Check production API health and recent backend container logs.', now() - interval '75 minutes'),
  ('demo-operator-session', 'ai', 'The API health endpoint is responding. Backend logs show intermittent timeout warnings but no container crash events.', now() - interval '74 minutes'),
  ('demo-developer-session', 'human', 'Show recent GitHub Actions runs for staging.', now() - interval '40 minutes'),
  ('demo-developer-session', 'ai', 'The latest staging workflow completed successfully. One earlier lint job failed and was retried successfully.', now() - interval '39 minutes'),
  ('demo-viewer-session', 'human', 'Summarize the execution history from today.', now() - interval '20 minutes'),
  ('demo-viewer-session', 'ai', 'Today includes successful health checks, a completed staging inspection, and one pending approval for a high-risk container operation.', now() - interval '19 minutes');

insert into approval_requests (
  id, session_id, requested_by, tool_name, tool_input, action, risk_level, summary, status, decided_by, decision_note, decided_at, created_at, expires_at
) values
  (
    '11111111-1111-4111-8111-111111111111',
    'demo-operator-session',
    'operator',
    'github_trigger_workflow',
    '{"repo_full_name":"example/smart-devops-assistant","workflow_id":"deploy-production.yml","ref":"main"}',
    'Trigger production deployment workflow',
    'critical',
    'Production workflow dispatch requires explicit human approval.',
    'pending',
    null,
    null,
    null,
    now() - interval '35 minutes',
    now() + interval '4 hours'
  ),
  (
    '22222222-2222-4222-8222-222222222222',
    'demo-admin-session',
    'admin',
    'docker_stop_container',
    '{"container_name":"legacy-worker"}',
    'Stop legacy worker container',
    'high',
    'Stopping this container may interrupt queue processing.',
    'approved',
    'admin',
    'Approved after confirming the replacement worker is healthy.',
    now() - interval '1 day',
    now() - interval '1 day 10 minutes',
    now() - interval '23 hours'
  ),
  (
    '33333333-3333-4333-8333-333333333333',
    'demo-developer-session',
    'devops.engineer',
    'docker_run_container',
    '{"image":"redis:7","name":"temporary-cache"}',
    'Run temporary Redis cache container',
    'high',
    'Container creation was rejected because the request did not include cleanup ownership.',
    'rejected',
    'operator',
    'Please use the staging namespace and add expiry labels.',
    now() - interval '2 days',
    now() - interval '2 days 15 minutes',
    now() - interval '2 days' + interval '4 hours'
  );

insert into executions (
  session_id, requested_by, tool_name, tool_input, status, summary, details, source, approval_id, started_at, completed_at
) values
  ('demo-admin-session', 'admin', 'docker_list_containers', '{}', 'completed', 'Listed running Docker containers for environment inspection.', '["docker_list_containers returned 5 running containers"]', 'agent', null, now() - interval '3 hours', now() - interval '3 hours' + interval '8 seconds'),
  ('demo-operator-session', 'operator', 'get_service_health', '{"url":"http://localhost:8000/health"}', 'completed', 'Backend API health check succeeded.', '["HTTP 200 returned in 42ms"]', 'agent', null, now() - interval '80 minutes', now() - interval '79 minutes'),
  ('demo-developer-session', 'devops.engineer', 'github_recent_runs', '{"repo_full_name":"example/smart-devops-assistant"}', 'completed', 'Fetched recent GitHub Actions workflow runs.', '["staging.yml completed", "lint.yml retried successfully"]', 'agent', null, now() - interval '45 minutes', now() - interval '44 minutes'),
  ('demo-viewer-session', 'viewer', 'get_system_metrics', '{}', 'completed', 'Returned read-only system metrics summary.', '["CPU 31%", "Memory 68%", "Disk 54%"]', 'agent', null, now() - interval '25 minutes', now() - interval '24 minutes'),
  ('demo-admin-session', 'admin', 'docker_stop_container', '{"container_name":"legacy-worker"}', 'completed', 'Approved by admin. Stopped legacy worker container after replacement validation.', 'Container stopped cleanly.', 'hitl', '22222222-2222-4222-8222-222222222222', now() - interval '1 day', now() - interval '1 day' + interval '12 seconds'),
  ('demo-developer-session', 'devops.engineer', 'docker_run_container', '{"image":"redis:7","name":"temporary-cache"}', 'cancelled', 'Rejected by operator. Temporary Redis cache container was not created.', 'Rejection note: Please use the staging namespace and add expiry labels.', 'hitl', '33333333-3333-4333-8333-333333333333', now() - interval '2 days', now() - interval '2 days');

commit;
