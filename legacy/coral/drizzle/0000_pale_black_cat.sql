CREATE TABLE `api_keys` (
	`id` text PRIMARY KEY NOT NULL,
	`organisation_id` text NOT NULL,
	`name` text NOT NULL,
	`key_prefix` text NOT NULL,
	`key_hash` text NOT NULL,
	`last_four` text NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`created_at` integer DEFAULT (unixepoch() * 1000) NOT NULL,
	`last_used_at` integer,
	`revoked_at` integer,
	FOREIGN KEY (`organisation_id`) REFERENCES `organisations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `api_keys_prefix_idx` ON `api_keys` (`key_prefix`);--> statement-breakpoint
CREATE UNIQUE INDEX `api_keys_hash_idx` ON `api_keys` (`key_hash`);--> statement-breakpoint
CREATE INDEX `api_keys_org_idx` ON `api_keys` (`organisation_id`);--> statement-breakpoint
CREATE TABLE `model_deployments` (
	`id` text PRIMARY KEY NOT NULL,
	`model_id` text NOT NULL,
	`infrastructure_provider` text,
	`infrastructure_region` text,
	`inference_country` text,
	`weight_country` text,
	`weight_location` text,
	`adapter` text NOT NULL,
	`status` text NOT NULL,
	`sovereignty_status` text NOT NULL,
	`sovereignty_verified_by` text,
	`sovereignty_verified_at` text,
	`sovereignty_verification_method` text,
	`synced_at` integer DEFAULT (unixepoch() * 1000) NOT NULL,
	FOREIGN KEY (`model_id`) REFERENCES `models`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `model_deployments_model_idx` ON `model_deployments` (`model_id`);--> statement-breakpoint
CREATE TABLE `models` (
	`id` text PRIMARY KEY NOT NULL,
	`api_model_id` text NOT NULL,
	`display_name` text NOT NULL,
	`creator` text,
	`intelligence_score` integer NOT NULL,
	`intelligence_score_source` text DEFAULT 'Artificial Analysis' NOT NULL,
	`model_version` text,
	`context_window` integer,
	`synced_at` integer DEFAULT (unixepoch() * 1000) NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `models_api_model_id_unique` ON `models` (`api_model_id`);--> statement-breakpoint
CREATE TABLE `organisations` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`slug` text NOT NULL,
	`country` text DEFAULT 'AU' NOT NULL,
	`abn` text,
	`contact_email` text,
	`status` text DEFAULT 'active' NOT NULL,
	`created_at` integer DEFAULT (unixepoch() * 1000) NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `organisations_slug_unique` ON `organisations` (`slug`);--> statement-breakpoint
CREATE TABLE `usage_events` (
	`id` text PRIMARY KEY NOT NULL,
	`request_id` text NOT NULL,
	`organisation_id` text,
	`api_key_id` text,
	`api_model_id` text,
	`deployment_id` text,
	`infrastructure_provider` text,
	`infrastructure_region` text,
	`inference_country` text,
	`streamed` integer DEFAULT false NOT NULL,
	`prompt_tokens` integer,
	`completion_tokens` integer,
	`total_tokens` integer,
	`latency_ms` integer NOT NULL,
	`status_code` integer NOT NULL,
	`error_code` text,
	`created_at` integer DEFAULT (unixepoch() * 1000) NOT NULL,
	FOREIGN KEY (`organisation_id`) REFERENCES `organisations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`api_key_id`) REFERENCES `api_keys`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `usage_events_org_idx` ON `usage_events` (`organisation_id`);--> statement-breakpoint
CREATE INDEX `usage_events_created_idx` ON `usage_events` (`created_at`);--> statement-breakpoint
CREATE INDEX `usage_events_model_idx` ON `usage_events` (`api_model_id`);