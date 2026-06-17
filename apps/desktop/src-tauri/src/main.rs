// Tauri desktop entry. See `lib.rs` for the actual run() function.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    aco_desktop_lib::run();
}
