
(define (problem circuit)
    (:domain Quantum)
    (:objects
        p0 p1 p2 p3 - pqubit
    )
    (:init
        (connected p0 p1)
        (connected p1 p2)
        (connected p2 p1)
        (connected p1 p0)
        (connected p1 p3)
        (connected p3 p1) 
        (free l0)
        (free l1)
        (free l2)
        (free l3)
    )
    (:goal
        (and
            (done g0)
            (done g1)
            (done g2)
            (done g3)
        )
    )
    (:metric minimize (total-time))
)
