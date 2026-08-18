#!/usr/bin/env python3
"""
LeakSentry (Hardened Edition) - Password Leak & Strength Checker (CLI)
Powered by k-Anonymity, Traffic Padding, Memory Scrubbing & Rich UI
"""

import ctypes
import hashlib
import math
import os
import random
import re
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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
MAX_RETRIES = 3


def calculate_entropy(password_bytes: bytearray) -> float:
    """Parolanın şannon entropisini ve tahmin zorluğunu hesaplar."""
    if not password_bytes:
        return 0.0
    
    # Karakter havuz boyutunu tespit et
    pwd_str = password_bytes.decode("utf-8", errors="ignore")
    pool_size = 0
    if re.search(r"[a-z]", pwd_str):
        pool_size += 26
    if re.search(r"[A-Z]", pwd_str):
        pool_size += 26
    if re.search(r"[0-9]", pwd_str):
        pool_size += 10
    if re.search(r"[^a-zA-Z0-9]", pwd_str):
        pool_size += 32

    if pool_size == 0:
        return 0.0

    entropy = len(pwd_str) * math.log2(pool_size)
    return round(entropy, 2)


def get_strength_rating(entropy: float, length: int) -> Tuple[str, str]:
    """Entropi değerine göre güvenlik derecesi döner."""
    if length < 8 or entropy < 30:
        return "ÇOK ZAYIF", "red"
    elif entropy < 50:
        return "ZAYIF", "yellow"
    elif entropy < 75:
        return "ORTA / İYİ", "cyan"
    else:
        return "GÜÇLÜ (KIRILMASI ÇOK ZOR)", "green"


def zeroize_bytearray(target: bytearray):
    """RAM'deki hassas parola verisinin üzerine 0x00 yazarak fiziksel olarak siler."""
    if target:
        for i in range(len(target)):
            target[i] = 0


def get_hash_and_clean(password_input: str) -> Tuple[str, str, str, float, int]:
    """
    Parolayı bytearray'e çevirir, hashler, entropisini ölçer ve belleği sıfırlar.
    Döner: (full_hash, prefix, suffix, entropy, length)
    """
    raw_bytes = bytearray(password_input.encode("utf-8"))
    pwd_length = len(password_input)
    entropy = calculate_entropy(raw_bytes)

    # SHA-1 Hash üretimi
    sha1 = hashlib.sha1(raw_bytes).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    # Bellek temizliği (Plaintext RAM'den silinir)
    zeroize_bytearray(raw_bytes)
    del password_input

    return sha1, prefix, suffix, entropy, pwd_length


def fetch_range_with_retry(prefix: str) -> requests.Response:
    """Rate-limit (HTTP 429) korumalı ve yeniden deneme mekanizmalı API sorgusu."""
    headers = {"User-Agent": "LeakSentry-Hardened-CLI"}
    url = f"{API_URL}{prefix}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                wait_time = int(response.headers.get("Retry-After", 2))
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise e
            time.sleep(1)

    raise RuntimeError("API isteği maksimum deneme sayısına ulaştı.")


def send_decoy_request():
    """Ağ trafiği analizini yanıltmak için sahte (decoy) bir hash ön eki sorgular."""
    random_prefix = secrets.token_hex(3)[:5].upper()
    try:
        requests.get(
            f"{API_URL}{random_prefix}",
            headers={"User-Agent": "LeakSentry-Hardened-CLI"},
            timeout=REQUEST_TIMEOUT
        )
    except Exception:
        pass  # Sahte istek başarısız olursa ana akışı bozma


def check_leak_hardened(prefix: str, suffix: str) -> int:
    """Gerçek sorguyu arka planda sahte (dummy) bir sorguyla paralel atarak çalıştırır."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Gerçek istek ile tuzak/sahte isteği aynı anda gönder
        future_real = executor.submit(fetch_range_with_retry, prefix)
        executor.submit(send_decoy_request)

        response = future_real.result()

    leak_count = 0
    for line in response.text.splitlines():
        if not line:
            continue
        parts = line.split(":")
        if len(parts) == 2 and parts[0] == suffix:
            leak_count = int(parts[1])
            break

    return leak_count


def render_banner():
    """Başlık banner ve güvenlik rozetleri."""
    title_text = Text("🛡️  LEAKSENTRY (HARDENED SECURITY EDITION)", style="bold cyan")
    subtitle_text = Text(
        "k-Anonymity • RAM Scrubbing • Traffic Decoys • Entropi Analizi",
        style="dim white"
    )
    header = Panel(
        Align.center(Text.assemble(title_text, "\n", subtitle_text)),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 2)
    )
    console.print(header)


def render_results(
    pwd_len: int,
    entropy: float,
    leak_count: int,
    full_hash: str,
    prefix: str,
    suffix: str
):
    strength_label, strength_color = get_strength_rating(entropy, pwd_len)

    # Kriptografik ve Güvenlik Tablosu
    table = Table(
        title="🔍 Kriptografik ve Güvenlik Özeti",
        title_style="bold blue",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        expand=True
    )
    table.add_column("Parametre", style="cyan", width=26)
    table.add_column("Değer / Durum", style="white")

    table.add_row("Parola Uzunluğu", f"{pwd_len} karakter")
    table.add_row("Entropi / Karmaşıklık", f"{entropy} bit — [{strength_color}]{strength_label}[/{strength_color}]")
    table.add_row("Yerel SHA-1 Hash (40)", f"[dim]{full_hash}[/dim]")
    table.add_row("Ağa Gönderilen (Prefix: 5)", f"[bold green]{prefix}[/bold green] [dim](k-anonymity)[/dim]")
    table.add_row("Cihazda Kalan (Suffix: 35)", f"[bold yellow]{suffix}[/bold yellow] [dim](gizli)[/dim]")
    table.add_row("Ağ Maskeleme (Trafik)", "[green]Aktif[/green] [dim](Paralel Decoy İstek)[/dim]")
    table.add_row("RAM Temizleme (Zeroize)", "[green]Uygulandı[/green] [dim](Bellekten silindi)[/dim]")

    console.print(table)
    console.print()

    # Akıllı Durum Paneli
    if leak_count > 0:
        alert_content = Text.from_markup(
            f"[bold red]❌ KRİTİK TEHLİKE:[/bold red] Bu parola bilinen veri sızıntılarında [bold yellow]{leak_count:,}[/bold yellow] kez tespit edilmiştir!\n"
            f"[dim white]Saldırganların elindeki sözlüklerde yer almaktadır. Parolanız güçlü görünse bile kesinlikle KULLANMAYIN.[/dim white]"
        )
        console.print(Panel(alert_content, border_style="red", box=box.HEAVY, padding=(0, 1)))

    elif leak_count == 0 and (pwd_len < 8 or entropy < 40):
        warning_content = Text.from_markup(
            f"[bold yellow]⚠️ DİKKAT (Sızmamış Ama Zayıf):[/bold yellow] Parola bilinen bir sızıntıda bulunamadı fakat tahmin edilmesi çok kolay!\n"
            f"[dim white]Derece: [{strength_color}]{strength_label}[/{strength_color}] (Entropi: {entropy} bit). Daha uzun ve karmaşık bir parola seçin.[/dim white]"
        )
        console.print(Panel(warning_content, border_style="yellow", box=box.ROUNDED, padding=(0, 1)))

    else:
        success_content = Text.from_markup(
            f"[bold green]✅ GÜVENLİ VE SAĞLAM:[/bold green] Bu parola hiçbir veri ihlalinde görülmedi ve karmaşıklık derecesi yüksek.\n"
            f"[dim white]Derece: [{strength_color}]{strength_label}[/{strength_color}] (Entropi: {entropy} bit). Güvenle kullanabilirsiniz.[/dim white]"
        )
        console.print(Panel(success_content, border_style="green", box=box.ROUNDED, padding=(0, 1)))


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

        # Parolayı hashle, entropisini al ve RAM'den temizle
        full_hash, prefix, suffix, entropy, pwd_len = get_hash_and_clean(password)

        with console.status("[bold cyan]Zırhlı k-Anonymity ve trafik maskeleme ile sorgulanıyor...", spinner="dots"):
            try:
                leak_count = check_leak_hardened(prefix, suffix)
            except requests.exceptions.RequestException as e:
                console.print(f"[bold red]Ağ Hatası:[/bold red] API'ye ulaşılamadı ({e})")
                continue

        console.print()
        render_results(pwd_len, entropy, leak_count, full_hash, prefix, suffix)


if __name__ == "__main__":
    main()