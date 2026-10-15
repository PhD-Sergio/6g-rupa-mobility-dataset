using Test
# Minimal modules avoid loading the simulator's full 2.6GB dependency graph.
module PrimitiveHarness
struct GeoPoint; lat::Float64; lon::Float64; end
function haversine_distance(a,b)
    x=sin(deg2rad(b.lat-a.lat)/2)^2+cos(deg2rad(a.lat))*cos(deg2rad(b.lat))*sin(deg2rad(b.lon-a.lon)/2)^2
    6371.0*2atan(sqrt(x),sqrt(1-x))
end
include("../src/Simulation/DistanceEvents.jl")
end
using .PrimitiveHarness
P = PrimitiveHarness.GeoPoint
T = (;gnb_locations=[P(0,0),P(0,1)],upf_locations=[P(0,0),P(0,1)],centralized_upf_locations=[P(0,0),P(0,1)])
@testset "distance observation" begin
    r=PrimitiveHarness.distance_primitives(T,1,2,1,2,1)
    @test r.nearest_psa == 2
    @test r.target_new_iupf_km == 0
    @test r.target_pinned_psa_km ≈ 111.19492664455873
    @test r.new_iupf_nearest_psa_km == 0
    @test r.level == 2
    @test PrimitiveHarness.distance_primitives(T,1,2,1,1,1).level == 1
    @test_throws ErrorException PrimitiveHarness.distance_primitives(T,1,2,1,2,3)
    io=IOBuffer(); PrimitiveHarness.DISTANCE_EVENT_IO[]=io
    PrimitiveHarness.DISTANCE_EVENT_COUNT[]=0
    sessions=[(;metadata=(;anchor_upf_index=1))]
    for _ in 1:3; PrimitiveHarness.record_distance_event!(nothing,T,sessions,1,2,1,2); end
    @test PrimitiveHarness.DISTANCE_EVENT_COUNT[] == 3
    @test length(split(chomp(String(take!(io))),'\n')) == 4
    PrimitiveHarness.DISTANCE_EVENT_IO[]=nothing
    PrimitiveHarness.record_distance_event!(nothing,T,sessions,1,2,1,2)
    @test PrimitiveHarness.DISTANCE_EVENT_COUNT[] == 3
end
