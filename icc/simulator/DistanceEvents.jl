# Opt-in observational capture; no RNG calls and no state-machine changes.
const DISTANCE_EVENT_IO = Ref{Union{Nothing,IO}}(nothing)
const DISTANCE_EVENT_COUNT = Ref(0)
# Simulation clock at the current handover, set by the caller before dispatch (observation only).
const DISTANCE_EVENT_TIME = Ref(NaN)
function distance_primitives(topology, old_gnb, new_gnb, old_upf, new_upf, pinned_psa)
    psas = topology.centralized_upf_locations
    isempty(psas) && error("Distance capture requires a two-tier topology")
    1 <= pinned_psa <= length(psas) || error("Invalid pinned PSA")
    old = topology.gnb_locations[old_gnb]
    target = topology.gnb_locations[new_gnb]
    oldedge = topology.upf_locations[old_upf]
    newedge = topology.upf_locations[new_upf]
    pin = psas[pinned_psa]
    nearest = argmin([haversine_distance(newedge, p) for p in psas])
    opt = psas[nearest]
    d = haversine_distance
    return (; old_gnb, target_gnb=new_gnb, old_iupf=old_upf, new_iupf=new_upf,
        pinned_psa, nearest_psa=nearest, level=old_upf == new_upf ? 1 : 2,
        old_gnb_target_km=d(old,target), target_old_iupf_km=d(target,oldedge),
        target_new_iupf_km=d(target,newedge), target_pinned_psa_km=d(target,pin),
        target_nearest_psa_km=d(target,opt), old_iupf_pinned_psa_km=d(oldedge,pin),
        new_iupf_pinned_psa_km=d(newedge,pin), new_iupf_nearest_psa_km=d(newedge,opt),
        old_new_iupf_km=d(oldedge,newedge))
end
function record_distance_event!(sim_state, topology, sessions, old_gnb, new_gnb, old_upf, new_upf)
    io = DISTANCE_EVENT_IO[]
    io === nothing && return
    isempty(sessions) && error("Handover without session cannot supply pinned PSA")
    row = distance_primitives(topology, old_gnb, new_gnb, old_upf, new_upf,
                              sessions[1].metadata.anchor_upf_index)
    DISTANCE_EVENT_COUNT[] += 1
    if DISTANCE_EVENT_COUNT[] == 1
        println(io, "event,t_s,session_count,", join(string.(keys(row)), ','))
    end
    println(io, DISTANCE_EVENT_COUNT[], ',', DISTANCE_EVENT_TIME[], ',', length(sessions), ',', join(values(row), ','))
end
