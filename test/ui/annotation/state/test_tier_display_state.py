from ui.annotation.state.tier_display_state import (
    TierDisplayState,
    hidden_and_order_from,
    tier_display_from,
)


def test_tier_display_numbers_tiers_from_the_bottom_in_the_order_given():
    assert tier_display_from(["a", "b", "c"], [], ["c", "a", "b"]) == [
        TierDisplayState("c", 1),
        TierDisplayState("a", 2),
        TierDisplayState("b", 3),
    ]


def test_tier_display_numbers_tiers_without_an_order_in_their_own_order():
    assert tier_display_from(["a", "b"], [], []) == [
        TierDisplayState("a", 1),
        TierDisplayState("b", 2),
    ]


def test_tier_display_puts_unordered_tiers_after_the_ordered_ones():
    assert tier_display_from(["a", "b", "c"], [], ["c"]) == [
        TierDisplayState("c", 1),
        TierDisplayState("a", 2),
        TierDisplayState("b", 3),
    ]


def test_tier_display_lists_hidden_tiers_last_without_a_position():
    assert tier_display_from(["a", "b", "c"], ["a"], ["a", "c"]) == [
        TierDisplayState("c", 1),
        TierDisplayState("b", 2),
        TierDisplayState("a"),
    ]


def test_hidden_and_order_from_hides_tiers_with_no_position():
    tiers = [TierDisplayState("a", 1), TierDisplayState("b")]

    assert hidden_and_order_from(tiers) == (["b"], ["a"])


def test_hidden_and_order_from_orders_tiers_by_position():
    tiers = [
        TierDisplayState("a", 3),
        TierDisplayState("b", 1),
        TierDisplayState("c", 2),
    ]

    assert hidden_and_order_from(tiers) == ([], ["b", "c", "a"])


def test_hidden_and_order_from_keeps_listed_order_for_equal_positions():
    tiers = [
        TierDisplayState("a", 2),
        TierDisplayState("b", 1),
        TierDisplayState("c", 2),
    ]

    assert hidden_and_order_from(tiers) == ([], ["b", "a", "c"])


def test_hidden_and_order_from_allows_gaps_in_the_numbers():
    tiers = [TierDisplayState("a", 5), TierDisplayState("b", 2)]

    assert hidden_and_order_from(tiers) == ([], ["b", "a"])


def test_hidden_and_order_from_can_hide_every_tier():
    tiers = [TierDisplayState("a"), TierDisplayState("b")]

    assert hidden_and_order_from(tiers) == (["a", "b"], [])


def test_what_tier_display_shows_round_trips_through_hidden_and_order():
    tiers = tier_display_from(["a", "b", "c"], ["b"], ["c", "a"])

    assert hidden_and_order_from(tiers) == (["b"], ["c", "a"])
