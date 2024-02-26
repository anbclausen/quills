
(define (domain Quantum)
    (:requirements :equality :typing :durative-actions)
    (:types
        pqubit gate lqubit - object
    )
    (:constants
        l0 l1 l2 l3 - lqubit
        g0 g1 g2 g3 - gate
    )
    (:predicates
        (occupied ?p - pqubit)
        (mapped ?l - lqubit ?p - pqubit)
        (connected ?p1 ?p2 - pqubit)
        (done ?g - gate)
        (free ?l - lqubit)
    )
    
    (:durative-action swap
        :parameters (?l1 ?l2 - lqubit ?p1 ?p2 - pqubit)
        :duration (= ?duration 3)
        :condition (and 
            (at start (mapped ?l1 ?p1))
            (at start (mapped ?l2 ?p2))
            (at start (connected ?p1 ?p2))
            (at start (free ?l1))
            (at start (free ?l2))
        )
        :effect (and 
            (at start (not (free ?l1)))
            (at start (not (free ?l2)))
            (at end (not (mapped ?l1 ?p1))) 
            (at end (not (mapped ?l2 ?p2)))
            (at end (mapped ?l1 ?p2))
            (at end (mapped ?l2 ?p1))
            (at end (free ?l1))
            (at end (free ?l2)) 
        )
    )

    (:durative-action apply_gate_g0
        :parameters (?p - pqubit)
        :duration (= ?duration 1)
        :condition (and 
            (at start (not (done g0)))
            (at start (not (occupied ?p)))
            (at start (free l0))
        )
        :effect (and 
            (at start (not (free l0)))
            (at start (occupied ?p))
            (at start (mapped l0 ?p))
            (at end (done g0))
            (at end (free l0))
        )
    )
    
    (:durative-action apply_cx_g1
        :parameters (?p1 ?p2 - pqubit)
        :duration (= ?duration 1)
        :condition (and 
            (at start (not (done g1)))
            (at start (connected ?p1 ?p2)) 
            (at start (not (occupied ?p1)))
            (at start (not (occupied ?p2)))
            (at start (free l2))
            (at start (free l3))
        )
        :effect (and 
            (at start (not (free l2)))
            (at start (not (free l3)))
            (at start (occupied ?p1))
            (at start (occupied ?p2)) 
            (at start (mapped l2 ?p1))
            (at start (mapped l3 ?p2))
            (at end (done g1)) 
            (at end (free l2))
            (at end (free l3))
        )
    )
    
    (:durative-action apply_cx_g2
        :parameters (?p1 ?p2 - pqubit)
        :duration (= ?duration 1)
        :condition (and 
            (at start (not (done g2)))
            (at start (done g0))
            (at start (connected ?p1 ?p2))
            (at start (mapped l0 ?p1))
            (at start (not (occupied ?p2)))
            (at start (free l0))
            (at start (free l1))
        )
        :effect (and 
            (at start (not (free l0)))
            (at start (not (free l1)))
            (at start (occupied ?p2))
            (at start (mapped l1 ?p2))
            (at end (done g2))
            (at end (free l0))
            (at end (free l1))
        )
    )
    
    (:durative-action apply_gate_g3
        :parameters (?p - pqubit)
        :duration (= ?duration 1)
        :condition (and 
            (at start (not (done g3)))
            (at start (done g1))
            (at start (mapped l2 ?p)) 
            (at start (free l2))
        )
        :effect (and 
            (at start (not (free l2)))
            (at end (done g3))
            (at end (free l2))
        )
    )
)
