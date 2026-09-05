from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EvolutionEdge:
    source: str
    target: str
    condition: str


# Evolution relationships are intentionally limited to species that have a concrete
# GE-1.0.0 Species DataAsset in this editor's catalog. A partial family therefore
# renders only the shipped members instead of inventing a selectable species.
EVOLUTION_EDGES = (
    EvolutionEdge("Abra", "Kadabra", "Lv. 16"),
    EvolutionEdge("Kadabra", "Alakazam", "Trade"),
    EvolutionEdge("Aron", "Lairon", "Lv. 32"),
    EvolutionEdge("Lairon", "Aggron", "Lv. 42"),
    EvolutionEdge("Azurill", "Marill", "Friendship"),
    EvolutionEdge("Marill", "Azumarill", "Lv. 18"),
    EvolutionEdge("Beldum", "Metang", "Lv. 20"),
    EvolutionEdge("Metang", "Metagross", "Lv. 45"),
    EvolutionEdge("Budew", "Roselia", "Friendship / day"),
    EvolutionEdge("Roselia", "Roserade", "Shiny Stone"),
    EvolutionEdge("Carvanha", "Sharpedo", "Lv. 30"),
    EvolutionEdge("Electrike", "Manectric", "Lv. 26"),
    EvolutionEdge("Geodude", "Graveler", "Lv. 25"),
    EvolutionEdge("Graveler", "Golem", "Trade"),
    EvolutionEdge("Goldeen", "Seaking", "Lv. 33"),
    EvolutionEdge("Gulpin", "Swalot", "Lv. 26"),
    EvolutionEdge("Kirlia", "Gallade", "Dawn Stone / male"),
    EvolutionEdge("Kirlia", "Gardevoir", "Lv. 30"),
    EvolutionEdge("Lotad", "Lombre", "Lv. 14"),
    EvolutionEdge("Lombre", "Ludicolo", "Water Stone"),
    EvolutionEdge("Machop", "Machoke", "Lv. 28"),
    EvolutionEdge("Machoke", "Machamp", "Trade"),
    EvolutionEdge("Magikarp", "Gyarados", "Lv. 20"),
    EvolutionEdge("Magnemite", "Magneton", "Lv. 30"),
    EvolutionEdge("Magneton", "Magnezone", "Special field"),
    EvolutionEdge("Makuhita", "Hariyama", "Lv. 24"),
    EvolutionEdge("Meditite", "Medicham", "Lv. 37"),
    EvolutionEdge("Mudkip", "Marshtomp", "Lv. 16"),
    EvolutionEdge("Marshtomp", "Swampert", "Lv. 36"),
    EvolutionEdge("Nincada", "Ninjask", "Lv. 20"),
    EvolutionEdge("Nincada", "Shedinja", "Lv. 20 / empty slot"),
    EvolutionEdge("Nosepass", "Probopass", "Special field"),
    EvolutionEdge("Poochyena", "Mightyena", "Lv. 18"),
    EvolutionEdge("Ralts", "Kirlia", "Lv. 20"),
    EvolutionEdge("Seedot", "Nuzleaf", "Lv. 14"),
    EvolutionEdge("Nuzleaf", "Shiftry", "Leaf Stone"),
    EvolutionEdge("Shroomish", "Breloom", "Lv. 23"),
    EvolutionEdge("Skitty", "Delcatty", "Moon Stone"),
    EvolutionEdge("Slakoth", "Vigoroth", "Lv. 18"),
    EvolutionEdge("Vigoroth", "Slaking", "Lv. 36"),
    EvolutionEdge("Slugma", "Magcargo", "Lv. 38"),
    EvolutionEdge("Taillow", "Swellow", "Lv. 22"),
    EvolutionEdge("Tentacool", "Tentacruel", "Lv. 30"),
    EvolutionEdge("Torchic", "Combusken", "Lv. 16"),
    EvolutionEdge("Combusken", "Blaziken", "Lv. 36"),
    EvolutionEdge("Treecko", "Grovyle", "Lv. 16"),
    EvolutionEdge("Grovyle", "Sceptile", "Lv. 36"),
    EvolutionEdge("Voltorb", "Electrode", "Lv. 30"),
    EvolutionEdge("Wailmer", "Wailord", "Lv. 40"),
    EvolutionEdge("Whismur", "Loudred", "Lv. 20"),
    EvolutionEdge("Loudred", "Exploud", "Lv. 40"),
    EvolutionEdge("Wingull", "Pelipper", "Lv. 25"),
    EvolutionEdge("Wurmple", "Cascoon", "Lv. 7 / personality"),
    EvolutionEdge("Wurmple", "Silcoon", "Lv. 7 / personality"),
    EvolutionEdge("Cascoon", "Dustox", "Lv. 10"),
    EvolutionEdge("Silcoon", "Beautifly", "Lv. 10"),
    EvolutionEdge("Zigzagoon", "Linoone", "Lv. 20"),
    EvolutionEdge("Zubat", "Golbat", "Lv. 22"),
    EvolutionEdge("Golbat", "Crobat", "Friendship"),
)


def evolution_family(species_name: str) -> tuple[tuple[str, ...], tuple[EvolutionEdge, ...]]:
    """Return topological layers and edges for the selected shipped-species family."""
    selected = species_name.casefold()
    undirected: dict[str, set[str]] = {}
    canonical: dict[str, str] = {}
    for edge in EVOLUTION_EDGES:
        source_key = edge.source.casefold()
        target_key = edge.target.casefold()
        canonical[source_key] = edge.source
        canonical[target_key] = edge.target
        undirected.setdefault(source_key, set()).add(target_key)
        undirected.setdefault(target_key, set()).add(source_key)
    if selected not in undirected:
        return ((species_name,),), ()

    component = {selected}
    pending = [selected]
    while pending:
        current = pending.pop()
        for neighbor in undirected.get(current, ()):
            if neighbor not in component:
                component.add(neighbor)
                pending.append(neighbor)
    edges = tuple(
        edge
        for edge in EVOLUTION_EDGES
        if edge.source.casefold() in component and edge.target.casefold() in component
    )
    indegree = {name: 0 for name in component}
    children: dict[str, list[str]] = {name: [] for name in component}
    for edge in edges:
        source_key = edge.source.casefold()
        target_key = edge.target.casefold()
        indegree[target_key] += 1
        children[source_key].append(target_key)
    roots = sorted((name for name, degree in indegree.items() if degree == 0), key=lambda key: canonical[key])
    depths: dict[str, int] = {name: 0 for name in roots}
    queue = list(roots)
    while queue:
        source = queue.pop(0)
        for target in children[source]:
            depths[target] = max(depths.get(target, 0), depths[source] + 1)
            queue.append(target)
    maximum = max(depths.values(), default=0)
    layers = tuple(
        tuple(sorted((canonical[name] for name, depth in depths.items() if depth == index), key=str.casefold))
        for index in range(maximum + 1)
    )
    return layers, edges
