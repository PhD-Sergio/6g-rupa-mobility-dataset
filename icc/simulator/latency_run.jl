using DesJulia6gRupa, Random, CSV, DataFrames, TOML, SHA
using ConcurrentSim
using DesJulia6gRupa.Types
using DesJulia6gRupa.DataLoading
using DesJulia6gRupa.Simulation
const S = DesJulia6gRupa.Simulation
# Usage: latency_run.jl MATRIX ROW OUT [AGENT_CAP] [DURATION]
row = CSV.read(ARGS[1], DataFrame)[parse(Int, ARGS[2]), :]
out = abspath(ARGS[3]); mkpath(out)
cap = length(ARGS) >= 4 ? parse(Int, ARGS[4]) : 0
secs = length(ARGS) >= 5 ? parse(Float64, ARGS[5]) : 1200.0
root = dirname(@__DIR__)
seed = Int(row.seed)
Random.seed!(seed)
# ICC_SCALE = users per agent (default 1000, as in every matrix run). A smaller scale
# keeps the represented population fixed and simulates proportionally more agents.
scale = parse(Int, get(ENV, "ICC_SCALE", "1000"))
agents = Int(row.agents) * 1000 ÷ scale
# ICC_HYST_DB = A3 offset in dB, mapped to a distance ratio 10^(dB/(10*alpha)) with
# path-loss exponent ICC_PL_EXP (default 3.5). 0 dB (default) keeps the nearest-gNB rule.
hyst_db = parse(Float64, get(ENV, "ICC_HYST_DB", "0"))
pl_exp = parse(Float64, get(ENV, "ICC_PL_EXP", "3.5"))
S.HANDOVER_HYSTERESIS[] = 10^(hyst_db / (10 * pl_exp))
n = cap > 0 ? min(cap, agents) : agents
profile(name) = name == "highway" ? GaussMarkov(120.0,0.85,5.0) :
        name == "urban" ? RandomWaypoint(50.0,0.0,20.0) : RandomWaypoint(5.0,0.0,2.0)
# "mix:P/U/H" assigns each agent pedestrian/urban/highway with those weights,
# drawn from a separate RNG so the simulation's global stream is not consumed here.
mix = startswith(String(row.mobility_model), "mix:") ?
    parse.(Float64, split(String(row.mobility_model)[5:end], '/')) : nothing
if mix === nothing
    model = profile(String(row.mobility_model)); S.AGENT_MOBILITY[] = nothing; mix_counts = nothing
else
    w = mix ./ sum(mix); cum = cumsum(w); pick = MersenneTwister(seed + 7919)
    names = ["pedestrian","urban","highway"]
    chosen = [names[findfirst(>=(rand(pick)), cum)] for _ in 1:n]
    S.AGENT_MOBILITY[] = MobilityModel[profile(c) for c in chosen]
    mix_counts = Dict(c => count(==(c), chosen) for c in names)
    model = profile("pedestrian")   # config placeholder; agents use their own model
end
config = SimConfig(1,2,scale,secs,secs-5.0,5.0,:two_tier,Int(row.psa),10.0,
    MobilityConfig(true,2.0,model))
data_dir = joinpath(root, "data", String(row.country))
# All official files preserve the simulator's operator encoding, not an invented MNC.
subdir = row.field == "fcc-asr" ? "asr" : row.field == "anfr" ? "anfr" : row.field == "ised" ? "ised" : "opencellid"
mccs = row.country == "usa" ? [310,311] :
       row.country == "spain" ? [214] : row.country == "france" ? [208] :
       row.country == "canada" ? [302] : row.country == "mexico" ? [334] : [268]
paths = filter(isfile, [joinpath(data_dir,subdir,"$m.csv") for m in mccs])
isempty(paths) && error("No input files for $(row.country)/$(row.field): $subdir")
topology = load_and_deploy_network(paths,Int(row.mnc),Int(row.edge_upf),data_dir,config)
state = init_global_state_for_simulation(topology,config)
simulation = ConcurrentSim.Simulation()
S.DISTANCE_EVENT_COUNT[] = 0
open(joinpath(out,"events.csv"),"w") do io
    S.DISTANCE_EVENT_IO[] = io
    try
        @process S.monitor_metrics(simulation,state,topology,config.scale_factor)
        for i in 1:n
            @process S.user_lifecycle(simulation,i,state,topology,eMBB)
        end
        run(simulation,secs)
    finally
        S.DISTANCE_EVENT_IO[] = nothing
    end
end
@assert S.DISTANCE_EVENT_COUNT[] == state.handover_count
provenance = Dict("seed"=>seed,"agents"=>n,"duration_s"=>secs,"handovers"=>state.handover_count,"scale_factor"=>scale,"hysteresis_db"=>hyst_db,"pathloss_exp"=>pl_exp,"mix_counts"=>something(mix_counts, Dict{String,Int}()),"core_writes_5g"=>state.core_writes_5g,"psa"=>Int(row.psa),
 "captured_events"=>S.DISTANCE_EVENT_COUNT[],"simulator_commit"=>strip(read(joinpath(root,"source-commit.txt"),String)),
 "julia"=>string(VERSION),"country"=>String(row.country),"field"=>String(row.field),
 "operator"=>String(row.operator),"speed_kmh"=>Float64(row.speed_kmh),
 "mobility_model"=>string(model),
 "instrumentation_sha256"=>bytes2hex(sha256(read(joinpath(root,"src/Simulation/DistanceEvents.jl")))),
 "modified_source_sha256"=>Dict(f=>bytes2hex(sha256(read(joinpath(root,f)))) for f in ["src/Simulation.jl","src/Simulation/Handover.jl","src/Simulation/DistanceEvents.jl","scripts/latency_run.jl"]),
 "matrix_sha256"=>bytes2hex(sha256(read(ARGS[1]))),
 "inputs"=>Dict(p=>bytes2hex(sha256(read(p))) for p in vcat(paths,[joinpath(data_dir,"municipalities.csv"),joinpath(data_dir,"regions.geojson")])) )
open(joinpath(out,"provenance.toml"),"w") do io; TOML.print(io,provenance); end
println("Captured $(state.handover_count) matched events in $out")
