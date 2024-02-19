(define (domain Quantum)
    (:requirements :strips :typing :negative-preconditions :action-costs)
    (:types
        pqubit gate depth lqubit - object
    )
    ;(:functions (total-cost))
    (:constants
        l0 l1 l2 l3 - lqubit
        g0 g1 g2 g3 - gate
    )
    (:predicates
        (occupied ?p - pqubit)
        (mapped ?l - lqubit ?p - pqubit)
        (connected ?p1 ?p2 - pqubit)
        (done ?g - gate)
        (busy ?l - lqubit)
        (is_swapping1 ?l1 ?l2 - lqubit)
        (is_swapping2 ?l1 ?l2 - lqubit)
        (is_swapping ?l - lqubit)
    )

    (:action swap
        :parameters (?l1 ?l2 - lqubit ?p1 ?p2 - pqubit)
        :precondition (and (mapped ?l1 ?p1) (mapped ?l2 ?p2) (connected ?p1 ?p2) (not (busy ?l1)) (not (busy ?l2)))
        :effect (and (not (mapped ?l1 ?p1)) (not (mapped ?l2 ?p2)) (mapped ?l1 ?p2) (mapped ?l2 ?p1) (busy ?l1) (busy ?l2) (is_swapping ?l1) (is_swapping ?l2) (is_swapping1 ?l1 ?l2))
    )

    (:action swap_dummy1
        :parameters (?l1 ?l2 - lqubit)
        :precondition (and (is_swapping1 ?l1 ?l2) (not (busy ?l1)) (not (busy ?l2)))
        :effect (and (not (is_swapping1 ?l1 ?l2)) (is_swapping2 ?l1 ?l2) (busy ?l1) (busy ?l2))
    )

    (:action swap_dummy2
        :parameters (?l1 ?l2 - lqubit)
        :precondition (and (is_swapping2 ?l1 ?l2) (not (busy ?l1)) (not (busy ?l2)))
        :effect (and (not (is_swapping2 ?l1 ?l2)) (not (is_swapping ?l1)) (not (is_swapping ?l2)) (busy ?l1) (busy ?l2))
    )
    
    (:action advance
        :effect (and (not (busy l0)) (not (busy l1)) (not (busy l2)) (not (busy l3)) 
        ;(increase (total-cost) 1)
        )
    )

    (:action apply_gate_g0
        :parameters (?p - pqubit)
        :precondition (and (not (done g0)) (not (occupied ?p)))
        :effect (and (done g0) (occupied ?p) (mapped l0 ?p) (busy l0))
    )

    (:action apply_cx_g1
        :parameters (?p1 ?p2 - pqubit)
        :precondition (and (not (done g1)) (connected ?p1 ?p2) (not (occupied ?p1)) (not (occupied ?p2)))
        :effect (and (done g1) (occupied ?p1) (occupied ?p2) (mapped l2 ?p1) (mapped l3 ?p2) (busy l2) (busy l3))
    )

    (:action apply_cx_g2
        :parameters (?p1 ?p2 - pqubit)
        :precondition (and (not (done g2)) (connected ?p1 ?p2) (done g0) (mapped l0 ?p1) (not (occupied ?p2)) (not (busy l0)) (not (is_swapping l0)))
        :effect (and (done g2) (occupied ?p2) (mapped l1 ?p2) (busy l0) (busy l1))
    )
    
    (:action apply_gate_g3
        :parameters (?p - pqubit)
        :precondition (and (not (done g3)) (done g1) (mapped l2 ?p) (not (busy l2)) (not (is_swapping l2)))
        :effect (and (done g3) (busy l2))
    )
)
