"""Yer imi yapisindan HTML uretimi ve kategori istatistikleri."""

from typing import Any, Dict

from bs4 import BeautifulSoup

Structure = Dict[str, Any]


def create_html_from_structure(structure: Structure, soup: BeautifulSoup) -> BeautifulSoup:
    """Duzenlenmis yer imi yapisindan standart HTML uretir."""
    def build_level(parent_dl: Any, level_dict: Dict[str, Any]) -> None:
        sorted_keys = sorted(level_dict.keys(), key=lambda k: (k == "__items__", k.lower()))

        for key in sorted_keys:
            if key == "__items__":
                continue

            dt_folder = soup.new_tag('DT')
            h3 = soup.new_tag('H3')
            h3.string = key
            dt_folder.append(h3)
            parent_dl.append(soup.new_tag('p'))

            sub_dl = soup.new_tag('DL')
            p_sub = soup.new_tag('p')
            sub_dl.append(p_sub)
            parent_dl.append(sub_dl)

            build_level(sub_dl, level_dict[key])

        if "__items__" in level_dict:
            for item in sorted(level_dict["__items__"], key=lambda x: x['title'].lower()):
                if item['type'] == 'link':
                    dt_link = soup.new_tag('DT')
                    a = soup.new_tag('A', href=item['url'])
                    if item.get('add_date'):
                        a['add_date'] = item['add_date']
                    if item.get('icon'):
                        a['icon'] = item['icon']
                    a.string = item['title']
                    dt_link.append(a)
                    parent_dl.append(dt_link)

    top_dl = soup.new_tag('DL')
    p_tag = soup.new_tag('p')
    top_dl.append(p_tag)
    build_level(top_dl, structure)
    return top_dl


def generate_statistics(structure: Structure) -> Dict[str, int]:
    """Kategori basina link sayilari uretir."""
    stats: Dict[str, int] = {}

    def count_items(level_dict: Dict[str, Any], path: str = "") -> int:
        total = 0
        for key, value in level_dict.items():
            if key == "__items__":
                count = len(value)
                if path:
                    stats[path] = count
                total += count
            else:
                current_path = f"{path} > {key}" if path else key
                total += count_items(value, current_path)
        return total

    total_count = count_items(structure)
    stats["TOPLAM"] = total_count
    return stats
