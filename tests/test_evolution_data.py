from __future__ import annotations

from gamma_editor.catalog import SPECIES
from gamma_editor.evolution_data import EVOLUTION_EDGES, evolution_family
from gamma_editor.sprites import sprite_filename


def test_evolution_edges_only_reference_shipped_species() -> None:
    names = {species.name for species in SPECIES}
    assert all(edge.source in names and edge.target in names for edge in EVOLUTION_EDGES)


def test_evolution_family_supports_linear_and_branching_charts() -> None:
    layers, edges = evolution_family("Treecko")
    assert layers == (("Treecko",), ("Grovyle",), ("Sceptile",))
    assert [edge.condition for edge in edges] == ["Lv. 16", "Lv. 36"]

    layers, edges = evolution_family("Gardevoir")
    assert layers == (("Ralts",), ("Kirlia",), ("Gallade", "Gardevoir"))
    assert {edge.target for edge in edges if edge.source == "Kirlia"} == {"Gallade", "Gardevoir"}


def test_sprite_filename_normalizes_catalog_spelling() -> None:
    assert sprite_filename("Torchic") == "TORCHIC.png"
    assert sprite_filename("MissingNo.") == "MISSINGNO.png"
    assert sprite_filename("Venasaur") == "VENUSAUR.png"
