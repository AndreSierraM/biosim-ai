/*
###############################################################################
# Adapted from the PhysiCell 1.14.2 template project (BSD 3-Clause, see      #
# vendor/licenses/). If you use PhysiCell, please cite:                      #
#                                                                             #
# We implemented and solved the model using PhysiCell (Version 1.14.2) [1].   #
#                                                                             #
# [1] A Ghaffarizadeh, R Heiland, SH Friedman, SM Mumenthaler, and P Macklin, #
#     PhysiCell: an Open Source Physics-Based Cell Simulator for Multicellu-  #
#     lar Systems, PLoS Comput. Biol. 14(2): e1005991, 2018                   #
#     DOI: 10.1371/journal.pcbi.1005991                                       #
###############################################################################
Tumor spheroid assay: a seeded cluster proliferates, consumes oxygen, and
develops a necrotic core. All behavior emerges from the engine —
no scripted motion phases.
*/

#include "./custom.h"

static int oxygen_substrate_index = 0;
static double o2_necrosis_threshold = 8.0;
static double o2_necrosis_max_rate = 0.002;
static int drug_substrate_index = 1;
static double drug_ec50 = 1.0;
static double drug_kill_max = 0.001;

void create_cell_types( void )
{
	// set the random seed
	if (parameters.ints.find_index("random_seed") != -1)
	{
		SeedRandom(parameters.ints("random_seed"));
	}

	initialize_default_cell_definition();
	cell_defaults.phenotype.secretion.sync_to_microenvironment( &microenvironment );

	cell_defaults.functions.volume_update_function = standard_volume_update_function;
	cell_defaults.functions.update_velocity = standard_update_cell_velocity;

	cell_defaults.functions.update_migration_bias = NULL;
	cell_defaults.functions.update_phenotype = NULL;
	cell_defaults.functions.custom_cell_rule = NULL;
	cell_defaults.functions.contact_function = NULL;

	cell_defaults.functions.add_cell_basement_membrane_interactions = NULL;
	cell_defaults.functions.calculate_distance_to_membrane = NULL;

	initialize_cell_definitions_from_pugixml();
	build_cell_definitions_maps();
	setup_signal_behavior_dictionaries();
	setup_cell_rules();

	oxygen_substrate_index = microenvironment.find_density_index( "oxygen" );
	o2_necrosis_threshold = parameters.doubles("o2_necrosis_threshold");
	o2_necrosis_max_rate = parameters.doubles("o2_necrosis_max_rate");

	drug_substrate_index = microenvironment.find_density_index( "drug" );
	drug_ec50 = parameters.doubles("drug_ec50");
	drug_kill_max = parameters.doubles("drug_kill_max");
	double drug_uptake = parameters.doubles("drug_uptake");
	for( int k=0; k < cell_definitions_by_index.size() ; k++ )
	{
		cell_definitions_by_index[k]->phenotype.secretion.uptake_rates[drug_substrate_index] = drug_uptake;
	}

	cell_defaults.functions.update_phenotype = phenotype_function;
	cell_defaults.functions.custom_cell_rule = custom_function;
	cell_defaults.functions.contact_function = contact_function;
	for( int k=0; k < cell_definitions_by_index.size() ; k++ )
	{
		cell_definitions_by_index[k]->functions.update_phenotype = phenotype_function;
	}

	display_cell_definitions( std::cout );

	return;
}

void setup_microenvironment( void )
{
	initialize_microenvironment();
	return;
}

void setup_tissue( void )
{
	int n = parameters.ints("initial_cells");
	Cell_Definition* pCD = cell_definitions_by_index[0];
	// 30 um: 12 cells (~10 um radius each) fill ~44% of the ball instead of
	// ~77% at 25 um: less initial overlap, still compact enough to grow a
	// necrotic core at full duration.
	double cluster_radius = 30.0;

	int placed = 0, guard = 0;
	while( placed < n && guard < 100000 )
	{
		guard++;
		double x = (2.0*UniformRandom()-1.0)*cluster_radius;
		double y = (2.0*UniformRandom()-1.0)*cluster_radius;
		double z = (2.0*UniformRandom()-1.0)*cluster_radius;
		if( x*x + y*y + z*z > cluster_radius*cluster_radius )
		{ continue; }
		Cell* pC = create_cell( *pCD );
		pC->assign_position( x, y, z );
		placed++;
	}
	std::cout << "Placed " << placed << " tumor cells in a "
		<< cluster_radius << " um cluster" << std::endl;

	return;
}

std::vector<std::string> my_coloring_function( Cell* pCell )
{ return paint_by_number_cell_coloring(pCell); }

void phenotype_function( Cell* pCell, Phenotype& phenotype, double dt )
{
	if( phenotype.death.dead == true )
	{ return; }
	std::vector<double> dens =
		pCell->get_microenvironment()->nearest_density_vector( pCell->position );
	double o2 = dens[oxygen_substrate_index];
	// Oxygen-gated proliferation (Monod kinetics on G0/G1 exit): hypoxic
	// cells linger in G0/G1 instead of cycling at full speed. K reuses the
	// necrosis threshold so one assay-scale parameter governs quiescence.
	// The base rate is captured once from the XML-calibrated definition.
	static double g0g1_base_rate = -1.0;
	if( g0g1_base_rate < 0.0 )
	{ g0g1_base_rate = phenotype.cycle.data.transition_rate(0,1); }
	double o2_factor = o2 / ( o2 + o2_necrosis_threshold );
	phenotype.cycle.data.transition_rate(0,1) = g0g1_base_rate * o2_factor;
	double rate = 0.0;
	if( o2 < o2_necrosis_threshold )
	{ rate = o2_necrosis_max_rate * (o2_necrosis_threshold - o2) / o2_necrosis_threshold; }
	int nidx = phenotype.death.find_death_model_index( PhysiCell_constants::necrosis_death_model );
	phenotype.death.rates[nidx] = rate;
	double drug = dens[drug_substrate_index];
	double kill = 0.0;
	if( drug > 0.0 && drug_kill_max > 0.0 )
	{ kill = drug_kill_max * drug / (drug + drug_ec50); }
	int aidx = phenotype.death.find_death_model_index( PhysiCell_constants::apoptosis_death_model );
	phenotype.death.rates[aidx] = kill;
	return;
}

void custom_function( Cell* pCell, Phenotype& phenotype , double dt )
{ return; }

void contact_function( Cell* pMe, Phenotype& phenoMe , Cell* pOther, Phenotype& phenoOther , double dt )
{ return; }
