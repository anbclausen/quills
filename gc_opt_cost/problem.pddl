(define (problem circuit)
    (:domain Quantum)
    (:objects
        p0 p1 p2 p3 - pqubit
    )
    (:init
        (connected p0 p1)
        (connected p1 p0)
        (connected p1 p2)
        (connected p2 p1)
        (connected p1 p3)
        (connected p3 p1)
        ;(connected p2 p3)
        ;(connected p3 p2)
        ;(= (total-cost) 0)
    )
    (:goal
        (and
            (done g0)
            (done g1)
            (done g2)
            (done g3)
            (not (is_swapping l0))
            (not (is_swapping l1))
            (not (is_swapping l2))
            (not (is_swapping l3))
        )
    )
    ;(:metric minimize (total-cost))
)