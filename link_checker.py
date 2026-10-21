import argparse
import sys
import os
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5,tr;q=0.3",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "about:", "data:", "file:", "ftp:")


@dataclass
class LinkResult:
    url: str
    title: str
    status: str  # "alive", "dead", "redirected", "error"
    http_status: Optional[int] = None
    redirect_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CheckReport:
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total: int = 0
    alive: int = 0
    dead: List[LinkResult] = field(default_factory=list)
    redirected: List[LinkResult] = field(default_factory=list)
    errors: List[LinkResult] = field(default_factory=list)
    skipped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "alive": self.alive,
            "dead": [
                {"url": r.url, "title": r.title, "status": r.http_status}
                for r in self.dead
            ],
            "redirected": [
                {
                    "url": r.url,
                    "title": r.title,
                    "status": r.http_status,
                    "redirect_url": r.redirect_url,
                }
                for r in self.redirected
            ],
            "errors": [
                {"url": r.url, "title": r.title, "error": r.error}
                for r in self.errors
            ],
            "skipped": self.skipped,
            "timestamp": self.timestamp,
        }

    def format_text(self) -> str:
        lines = [
            "=== DEAD LINK CHECKER RAPORU ===",
            f"Tarih: {self.timestamp}",
            f"Toplam Link: {self.total}",
            f"Aktif: {self.alive}",
            f"Ölü: {len(self.dead)}",
            f"Yönlendirme: {len(self.redirected)}",
            f"Hata: {len(self.errors)}",
            f"Atlanan: {self.skipped}",
            "",
        ]

        if self.dead:
            lines.append("--- ÖLÜ LİNKLAR ---")
            for r in self.dead:
                status_label = r.http_status if r.http_status else "Timeout"
                lines.append(f"[{status_label}] {r.url} - {r.title}")
            lines.append("")

        if self.redirected:
            lines.append("--- YÖNLENDİRME LİNKLAR ---")
            for r in self.redirected:
                lines.append(f"[{r.http_status}] {r.url} -> {r.redirect_url}")
            lines.append("")

        if self.errors:
            lines.append("--- HATA LİNKLAR ---")
            for r in self.errors:
                lines.append(f"[Hata: {r.error}] {r.url} - {r.title}")
            lines.append("")

        return "\n".join(lines)


def check_single_url(url: str, timeout: int = 10, verify: bool = True) -> LinkResult:
    """Check if a single URL is alive. Returns LinkResult with status classification.

    TLS doğrulaması varsayılan olarak AÇIKTIR; `verify=False` yalnızca
    `--insecure` bayrağı ile (bilinçli olarak) kullanılır.
    """
    try:
        resp = requests.head(
            url,
            headers=REQUEST_HEADERS,
            timeout=timeout,
            allow_redirects=False,
            verify=verify,
        )

        if resp.status_code in (405, 403, 401, 501):
            resp = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
                verify=verify,
            )
            resp.close()

    except requests.exceptions.Timeout:
        return LinkResult(url=url, title="", status="error", error="timeout")
    except requests.exceptions.SSLError:
        if not verify:
            return LinkResult(url=url, title="", status="error", error="ssl_error")
        try:
            resp = requests.head(
                url,
                headers=REQUEST_HEADERS,
                timeout=timeout,
                allow_redirects=False,
                verify=verify,
            )
        except requests.exceptions.RequestException:
            return LinkResult(url=url, title="", status="error", error="ssl_error")
    except requests.exceptions.ConnectionError:
        return LinkResult(url=url, title="", status="error", error="connection_error")
    except requests.exceptions.TooManyRedirects:
        return LinkResult(url=url, title="", status="error", error="too_many_redirects")
    except requests.exceptions.RequestException as exc:
        return LinkResult(url=url, title="", status="error", error=str(exc)[:120])

    status_code = resp.status_code

    if 200 <= status_code < 300:
        return LinkResult(url=url, title="", status="alive", http_status=status_code)

    if status_code in (301, 302, 303, 307, 308):
        redirect_url = resp.headers.get("Location", "")
        return LinkResult(
            url=url, title="", status="redirected",
            http_status=status_code, redirect_url=redirect_url,
        )

    # 403 → often bot-blocked but link is alive
    if status_code == 403:
        return LinkResult(url=url, title="", status="alive", http_status=403)

    if status_code == 404:
        return LinkResult(url=url, title="", status="dead", http_status=404)

    return LinkResult(url=url, title="", status="dead", http_status=status_code)


def _should_skip(url: str) -> bool:
    lower = url.strip().lower()
    return any(lower.startswith(scheme) for scheme in SKIP_SCHEMES)


def _extract_links(html_path: str) -> List[Dict[str, str]]:
    with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    links: List[Dict[str, str]] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        url = str(href).strip() if href else ""
        title = anchor.get_text(strip=True)
        if url:
            links.append({"url": url, "title": title or url})
    return links


def check_links(
    input_file: str,
    output_report: Optional[str] = None,
    timeout: int = 10,
    max_workers: int = 5,
    verify: bool = True,
) -> Dict[str, Any]:
    """Check all links in an HTML bookmark file. Returns report dict."""
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Bookmark dosyası bulunamadı: {input_file}")

    links = _extract_links(input_file)
    logger.info("Dosyadan %d link çıkarıldı: %s", len(links), input_file)

    report = CheckReport()
    report.total = len(links)

    to_check: List[Dict[str, str]] = []
    for item in links:
        if _should_skip(item["url"]):
            report.skipped += 1
        else:
            to_check.append(item)

    logger.info("Kontrol edilecek: %d, atlanan: %d", len(to_check), report.skipped)

    checked = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(check_single_url, item["url"], timeout, verify): item
            for item in to_check
        }

        for future in as_completed(future_map):
            item = future_map[future]
            result: LinkResult = future.result()
            result.title = item["title"]

            checked += 1
            if checked % 25 == 0 or checked == len(to_check):
                logger.info("İlerleme: %d/%d kontrol edildi", checked, len(to_check))

            if result.status == "alive":
                report.alive += 1
            elif result.status == "dead":
                report.dead.append(result)
            elif result.status == "redirected":
                report.redirected.append(result)
            else:
                report.errors.append(result)

    report.dead.sort(key=lambda r: r.url)
    report.redirected.sort(key=lambda r: r.url)
    report.errors.sort(key=lambda r: r.url)

    text_report = report.format_text()
    logger.info("\n%s", text_report)

    if output_report:
        try:
            with open(output_report, "w", encoding="utf-8") as fh:
                fh.write(text_report)
            logger.info("Rapor kaydedildi: %s", output_report)
        except OSError as exc:
            logger.error("Rapor kaydedilemedi: %s", exc)

    return report.to_dict()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HTML bookmark dosyasındaki linklerin canlılık kontrolü."
    )
    parser.add_argument(
        "input_file",
        help="Kontrol edilecek HTML bookmark dosyası",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Rapor dosyası yolu (opsiyonel)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=10,
        help="HTTP timeout süresi, saniye (varsayılan: 10)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=5,
        help="Eşzamanlı thread sayısı (varsayılan: 5)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="TLS sertifika doğrulamasını kapatır (önerilmez)",
    )
    return parser


def main() -> None:
    import urllib3

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = _build_parser()
    args = parser.parse_args()

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("TLS doğrulaması kapatıldı (--insecure)")

    try:
        result = check_links(
            input_file=args.input_file,
            output_report=args.output,
            timeout=args.timeout,
            max_workers=args.workers,
            verify=not args.insecure,
        )
        sys.exit(1 if result["dead"] else 0)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(2)
    except KeyboardInterrupt:
        logger.warning("Kullanıcı tarafından iptal edildi.")
        sys.exit(130)


if __name__ == "__main__":
    main()
