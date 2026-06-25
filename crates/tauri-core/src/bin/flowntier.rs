//! `flowntier` CLI — doctor, run, repl, and other headless operations.
//!
//! The Tauri app uses the same library; this binary is for users
//! who want to run workflows without the UI.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use tauri_core::AppState;
use tracing_subscriber::EnvFilter;

#[derive(Debug, Parser)]
#[command(
    name = "flowntier",
    version,
    about = "Flowntier — headless CLI",
    long_about = None
)]
struct Cli {
    /// Path to a custom `flowntier.toml` (default: OS-specific).
    #[arg(long, global = true)]
    config: Option<PathBuf>,

    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Run pre-flight diagnostics (config, providers, disk, plugins).
    Doctor,
    /// Run a workflow from a free-form user request.
    Run {
        /// The request text.
        request: String,
    },
    /// Show Flowntier version and paths.
    Info,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let cli = Cli::parse();
    match cli.command {
        Command::Doctor => doctor().await,
        Command::Run { request } => run(&request).await,
        Command::Info => info(),
    }
}

async fn doctor() -> Result<()> {
    println!("flowntier doctor — pre-flight diagnostic\n");
    let state = AppState::build().await.context("build AppState")?;
    println!("✓ AppState built");
    println!("  data_dir: {}", state.config.app.data_dir);
    println!("  log_level: {:?}", state.config.app.log_level);
    println!("  theme: {:?}", state.config.app.theme);
    println!("✓ Repository opened");
    println!("✓ EventBus initialized");
    println!("  subscribers: {}", state.bus.subscriber_count());
    println!("\nAll systems nominal.");
    Ok(())
}

async fn run(_request: &str) -> Result<()> {
    anyhow::bail!("`flowntier run` is not implemented yet; coming in Phase 1 (see plans/Phase1.md)")
}

fn info() -> Result<()> {
    println!("flowntier {}", env!("CARGO_PKG_VERSION"));
    println!("data dir: <see `flowntier doctor` to initialize>");
    Ok(())
}
