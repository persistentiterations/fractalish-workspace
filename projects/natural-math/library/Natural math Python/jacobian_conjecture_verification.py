"""
Verification of Counterexamples to the Jacobian Conjecture
July 2026 - Alpoge/Fable (C^3) and GPT-5.6 (C^4) counterexamples

The Jacobian Conjecture (Keller, 1939) stated:
If F: C^n -> C^n is a polynomial map with constant non-zero Jacobian determinant,
then F is a polynomial automorphism (bijective with polynomial inverse).

These counterexamples show polynomial maps with constant non-zero Jacobian
that are NOT injective.

Run with: python jacobian_conjecture_verification.py
Requires: sympy
"""

import sympy as sp
from sympy import symbols, expand, simplify, Rational, Matrix, Poly


def verify_counterexample_3d():
    """Verify the Alpoge/Fable counterexample in C^3."""
    print("=" * 70)
    print("COUNTEREXAMPLE 1: Alpoge / Fable - Map from C^3 to C^3")
    print("=" * 70)

    x, y, z = symbols("x y z")

    # Define the polynomial map F = (f1, f2, f3)
    f1 = (1 + x * y) ** 3 * z + y ** 2 * (1 + x * y) * (4 + 3 * x * y)
    f2 = y + 3 * x * (1 + x * y) ** 2 * z + 3 * x * y ** 2 * (4 + 3 * x * y)
    f3 = 2 * x - 3 * x ** 2 * y - x ** 3 * z

    print("\n--- Polynomial Components ---")
    print("f1 =", expand(f1))
    print("f2 =", expand(f2))
    print("f3 =", expand(f3))

    # Verify they are polynomials
    assert f1.is_polynomial(x, y, z), "f1 is not a polynomial!"
    assert f2.is_polynomial(x, y, z), "f2 is not a polynomial!"
    assert f3.is_polynomial(x, y, z), "f3 is not a polynomial!"
    print("\nAll components verified as polynomials: YES")

    # Compute total degrees
    print("\n--- Degrees ---")
    print("deg(f1) =", Poly(f1, x, y, z).total_degree())
    print("deg(f2) =", Poly(f2, x, y, z).total_degree())
    print("deg(f3) =", Poly(f3, x, y, z).total_degree())

    # Compute Jacobian matrix
    J = Matrix(
        [
            [sp.diff(f1, x), sp.diff(f1, y), sp.diff(f1, z)],
            [sp.diff(f2, x), sp.diff(f2, y), sp.diff(f2, z)],
            [sp.diff(f3, x), sp.diff(f3, y), sp.diff(f3, z)],
        ]
    )

    print("\n--- Jacobian Matrix ---")
    for i in range(3):
        print(f"Row {i + 1}: {J[i, :]}")

    # Compute and verify Jacobian determinant
    det_J = simplify(sp.det(J))
    print("\n--- Jacobian Determinant ---")
    print("det(J) =", det_J)
    assert det_J == -2, f"Expected det(J) = -2, got {det_J}"
    print("Verified: det(J) == -2 (constant, non-zero)")

    # Define the three claimed collision points
    p1 = (Rational(0), Rational(0), Rational(-1, 4))
    p2 = (Rational(1), Rational(-3, 2), Rational(13, 2))
    p3 = (Rational(-1), Rational(3, 2), Rational(13, 2))

    # Evaluate the map at a point
    def eval_map(px, py, pz):
        return (
            simplify(f1.subs([(x, px), (y, py), (z, pz)])),
            simplify(f2.subs([(x, px), (y, py), (z, pz)])),
            simplify(f3.subs([(x, px), (y, py), (z, pz)])),
        )

    target = (Rational(-1, 4), Rational(0), Rational(0))

    print("\n--- Collision Verification ---")
    result_p1 = eval_map(*p1)
    result_p2 = eval_map(*p2)
    result_p3 = eval_map(*p3)

    print(f"F{p1} = {result_p1}")
    print(f"F{p2} = {result_p2}")
    print(f"F{p3} = {result_p3}")

    assert result_p1 == target, f"p1 mismatch: {result_p1} != {target}"
    assert result_p2 == target, f"p2 mismatch: {result_p2} != {target}"
    assert result_p3 == target, f"p3 mismatch: {result_p3} != {target}"
    print(f"\nAll three points map to {target}: VERIFIED")

    # Verify points are distinct
    assert len({p1, p2, p3}) == 3, "Points are not all distinct!"
    print("\nAll three input points are distinct: VERIFIED")

    print("\n" + "=" * 70)
    print("C^3 COUNTEREXAMPLE: VERIFIED")
    print("=" * 70)
    return True


def verify_counterexample_4d():
    """Verify the GPT-5.6 counterexample in C^4."""
    print("\n" + "=" * 70)
    print("COUNTEREXAMPLE 2: GPT-5.6 - Map from C^4 to C^4")
    print("=" * 70)

    x, y, z, w = symbols("x y z w")

    # Define the polynomial map G = (g1, g2, g3, g4)
    g1 = -(1 + x * y) ** 2 * z - y ** 3 * (1 + x * y)
    g2 = (
        2 * x * (1 + x * y) * z
        + (1 + x * y) ** 3 * w
        + y ** 2 * (7 + 12 * x * y + 4 * x ** 2 * y ** 2)
    )
    g3 = (
        2 * x ** 2 * z
        + 3 * x * (1 + x * y) ** 2 * w
        + 2 * y * (1 + 10 * x * y + 6 * x ** 2 * y ** 2)
    )
    g4 = 2 * x - 4 * x ** 2 * y - x ** 3 * w

    print("\n--- Polynomial Components ---")
    print("g1 =", expand(g1))
    print("g2 =", expand(g2))
    print("g3 =", expand(g3))
    print("g4 =", expand(g4))

    # Verify they are polynomials
    assert g1.is_polynomial(x, y, z, w), "g1 is not a polynomial!"
    assert g2.is_polynomial(x, y, z, w), "g2 is not a polynomial!"
    assert g3.is_polynomial(x, y, z, w), "g3 is not a polynomial!"
    assert g4.is_polynomial(x, y, z, w), "g4 is not a polynomial!"
    print("\nAll components verified as polynomials: YES")

    # Compute total degrees
    print("\n--- Degrees ---")
    print("deg(g1) =", Poly(g1, x, y, z, w).total_degree())
    print("deg(g2) =", Poly(g2, x, y, z, w).total_degree())
    print("deg(g3) =", Poly(g3, x, y, z, w).total_degree())
    print("deg(g4) =", Poly(g4, x, y, z, w).total_degree())

    # Compute Jacobian matrix
    J4 = Matrix(
        [
            [
                sp.diff(g1, x),
                sp.diff(g1, y),
                sp.diff(g1, z),
                sp.diff(g1, w),
            ],
            [
                sp.diff(g2, x),
                sp.diff(g2, y),
                sp.diff(g2, z),
                sp.diff(g2, w),
            ],
            [
                sp.diff(g3, x),
                sp.diff(g3, y),
                sp.diff(g3, z),
                sp.diff(g3, w),
            ],
            [
                sp.diff(g4, x),
                sp.diff(g4, y),
                sp.diff(g4, z),
                sp.diff(g4, w),
            ],
        ]
    )

    print("\n--- Jacobian Matrix ---")
    for i in range(4):
        print(f"Row {i + 1}: {J4[i, :]}")

    # Compute and verify Jacobian determinant
    det_J4 = simplify(sp.det(J4))
    print("\n--- Jacobian Determinant ---")
    print("det(J4) =", det_J4)
    assert det_J4 == 4, f"Expected det(J4) = 4, got {det_J4}"
    print("Verified: det(J4) == 4 (constant, non-zero)")

    # Define the four claimed collision points
    pts = [
        (Rational(-2), Rational(0), Rational(1), Rational(0)),
        (Rational(-1), Rational(0), Rational(1), Rational(-2)),
        (Rational(1), Rational(-2), Rational(-7), Rational(14)),
        (Rational(2), Rational(-1), Rational(0), Rational(3)),
    ]

    # Evaluate the map at a point
    def eval_map(px, py, pz, pw):
        return (
            simplify(g1.subs([(x, px), (y, py), (z, pz), (w, pw)])),
            simplify(g2.subs([(x, px), (y, py), (z, pz), (w, pw)])),
            simplify(g3.subs([(x, px), (y, py), (z, pz), (w, pw)])),
            simplify(g4.subs([(x, px), (y, py), (z, pz), (w, pw)])),
        )

    target = (Rational(-1), Rational(-4), Rational(8), Rational(-4))

    print("\n--- Collision Verification ---")
    for i, p in enumerate(pts):
        result = eval_map(*p)
        print(f"Point {i + 1}: {p}")
        print(f"  -> {result}")
        assert result == target, f"Point {i + 1} mismatch: {result} != {target}"
        print(f"  Matches target? YES")

    # Verify points are distinct
    assert len(set(pts)) == 4, "Points are not all distinct!"
    print("\nAll four input points are distinct: VERIFIED")

    print("\n" + "=" * 70)
    print("C^4 COUNTEREXAMPLE: VERIFIED")
    print("=" * 70)
    return True


def main():
    """Run all verifications and print final summary."""
    ok_3d = verify_counterexample_3d()
    ok_4d = verify_counterexample_4d()

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print("\nThe Jacobian Conjecture stated:")
    print(
        "  If F: C^n -> C^n is polynomial with constant non-zero Jacobian,"
    )
    print("  then F is bijective with polynomial inverse.")
    print("\nThese counterexamples demonstrate:")
    print("  - In C^3: A polynomial map with det(J) = -2 that is NOT injective")
    print("  - In C^4: A polynomial map with det(J) = 4 that is NOT injective")
    print("\nTherefore:")
    print("  - The Jacobian Conjecture is FALSE for all n >= 3")
    print("  - The n = 2 case remains open (and is now the central problem)")
    print("\nKey insight: Local invertibility (non-zero Jacobian everywhere)")
    print("does NOT imply global invertibility for polynomial maps in n >= 3.")
    print("The 'fold' that would normally create a vanishing Jacobian is")
    print("pushed to infinity, where the Jacobian cannot detect it.")
    print("\n" + "=" * 70)
    print(f"All verifications passed: {ok_3d and ok_4d}")
    print("=" * 70)


if __name__ == "__main__":
    main()
