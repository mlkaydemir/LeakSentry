#!/usr/bin/env python3
"""
LeakSentry - Password Leak Checker (CLI)
Powered by k-Anonymity & Rich UI
"""

import hashlib
import sys
from typing import Tuple

import requests
from prompt_toolkit import prompt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

console = Console()
API_URL = "https://api.pwnedpasswords.com/range/"
REQUEST_TIMEOUT = 6


def get_hash_parts(password: str) -> Tuple[str, str, str]:
    """Parolayı SHA-1 ile hashler (40 karakter). İlk 5 ve kalan 35 karakteri ayırır."""
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    return sha1, sha1[:5], sha1[5:]


def fetch_hibp_range(prefix: str) -> requests.Response:
    """HIBP Range API'sine sadece 5 karakterlik prefix'i gönderir."""
    headers = {"User-Agent": "LeakSentry-CLI-Production"}
    response = requests.get(f"{API_URL}{prefix}", headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def check_leak(password: str) -> Tuple[int, str, str, str]:
    """k-Anonymity sorgusunu yürütür ve yerel eşleştirme yapar."""
    full_hash, prefix, suffix = get_hash_parts(password)
    response = fetch_hibp_range(prefix)

    leak_count = 0
    for line in response.text.splitlines():
        if not line:
            continue
        parts = line.split(":")
        if len(parts) == 2:
            api_suffix, count = parts
            if api_suffix == suffix:
                leak_count = int(count)
                break

    return leak_count, full_hash, prefix, suffix


def render_banner():
    """Üst karşılama ve bilgi paneli."""
    title_text = Text("🛡️  LEAKSENTRY: PAROLA SIZINTI KONTROLCÜSÜ", style="bold cyan")
    subtitle_text = Text(
        "Have I Been Pwned API • k-Anonymity Modeli • Sıfır Bilgi Güvenliği",
        style="dim white"
    )
    header = Panel(
        Align.center(Text.assemble(title_text, "\n", subtitle_text)),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 2)
    )
    console.print(header)


def render_results(password_len: int, leak_count: int, full_hash: str, prefix: str, suffix: str):
    """Teknik özet tablosu ve durum paneli."""
    table = Table(
        title="🔍 Kriptografik ve Ağ Özeti",
        title_style="bold blue",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        expand=True
    )
    table.add_column("Parametre", style="cyan", width=26)
    table.add_column("Değer / Durum", style="white")

    table.add_row("Parola Uzunluğu", f"{password_len} karakter")
    table.add_row("Yerel SHA-1 Hash (40)", f"[dim]{full_hash}[/dim]")
    table.add_row(
        "Sunucuya Gönderilen (Prefix: 5)",
        f"[bold green]{prefix}[/bold green] [dim](k-anonymity grubu)[/dim]"
    )
    table.add_row(
        "Cihazda Kalan (Suffix: 35)",
        f"[bold yellow]{suffix}[/bold yellow] [dim](gizli tutulan)[/dim]"
    )

    console.print(table)
    console.print()

    if leak_count > 0:
        alert_content = Text.from_markup(
            f"[bold red]❌ TEHLİKE:[/bold red] Bu parola veri sızıntılarında [bold yellow]{leak_count:,}[/bold yellow] kez tespit edilmiştir!\n"
            f"[dim white]Saldırganların listelerinde mevcuttur. Bu parolayı aktif hiçbir hesapta kullanmayın.[/dim white]"
        )
        alert_panel = Panel(
            alert_content,
            border_style="red",
            box=box.HEAVY,
            padding=(0, 1)
        )
    else:
        success_content = Text.from_markup(
            "[bold green]✅ TEMİZ:[/bold green] Bu parola bilinen hiçbir veri sızıntısında görülmedi.\n"
            "[dim white]Not: Güvenliğiniz için yine de tahmin edilemez ve benzersiz kombinasyonlar kullanın.[/dim white]"
        )
        alert_panel = Panel(
            success_content,
            border_style="green",
            box=box.ROUNDED,
            padding=(0, 1)
        )

    console.print(alert_panel)


def main():
    console.clear()
    render_banner()

    while True:
        try:
            console.print("\n" + "─" * 65, style="dim")
            password = prompt("🔑 Parola girin (Çıkış için 'q'): ", is_password=True)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Program sonlandırıldı. Görüşmek üzere![/yellow]\n")
            break

        if password.strip().lower() == "q":
            console.print("\n[yellow]Çıkış yapıldı. Güvenli günler dileriz![/yellow]\n")
            break

        if not password:
            console.print("[red]Boş parola girdiniz, lütfen tekrar deneyin.[/red]")
            continue

        with console.status("[bold cyan]HIBP veritabanı k-Anonymity ile taranıyor...", spinner="dots"):
            try:
                leak_count, full_hash, prefix, suffix = check_leak(password)
            except requests.exceptions.RequestException as e:
                console.print(f"[bold red]Ağ Hatası:[/bold red] Servise ulaşılamadı ({e})")
                continue

        console.print()
        render_results(len(password), leak_count, full_hash, prefix, suffix)


if __name__ == "__main__":
    main()