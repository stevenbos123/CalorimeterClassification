// ======================================================================
// Project Name    : EPICAl-2
// File Name       : convert_raw_data.cxx
// Authour         : T. Rogoschinski
// Last Update     : 28.10.2022
// Description     : Read EPICAL-2 raw data and create xy projections on
//					plane of quantized size.
// 					It takes the raw root input file of size 1024x1024x24 and outputs a root 
//					file where the data is in array per event with the 
//					number of hits at each pixel, 0 if none. 
//					This file is now set to quantize to 32x32 images.
//					The data is not normalized so just raw hit numbers 
//					per pixel.
// ======================================================================

#include <iostream>
#include <string.h>
#include <vector>
#include <fstream>
#include <math.h>
const std::map< Int_t, Int_t > chipid2lane_lut = {
	{ 0,40},{ 1,39},{ 2,42},{ 3,41},{ 4,44},{ 5,43},{ 6,46},{ 7,45},
	{ 8,48},{ 9,47},{10,50},{11,49},{12,52},{13,51},{14,54},{15,53},
	{16,38},{17,55},{18,36},{19,37},{20,32},{21,35},{22,34},{23,33},
	{24,64},{25,63},{26,66},{27,65},{28,68},{29,67},{30,70},{31,69},
	{32,72},{33,71},{34,74},{35,73},{36,76},{37,75},{38,78},{39,77},
	{40,62},{41,79},{42,60},{43,61},{44,56},{45,59},{46,58},{47,57}
};

const std::map< Int_t, Int_t > lane2chipid_lut = {
	{40, 0},{39, 1},{42, 2},{41, 3},{44, 4},{43, 5},{46, 6},{45, 7},
	{48, 8},{47, 9},{50,10},{49,11},{52,12},{51,13},{54,14},{53,15},
	{38,16},{55,17},{36,18},{37,19},{32,20},{35,21},{34,22},{33,23},
	{64,24},{63,25},{66,26},{65,27},{68,28},{67,29},{70,30},{69,31},
	{72,32},{71,33},{74,34},{73,35},{76,36},{75,37},{78,38},{77,39},
	{62,40},{79,41},{60,42},{61,43},{56,44},{59,45},{58,46},{57,47}
};

const std::map< Int_t, Int_t > chipid2layer_lut = {
	{ 0,22},{ 1,22},{ 2,20},{ 3,20},{ 4,18},{ 5,18},{ 6,16},{ 7,16},
	{ 8,14},{ 9,14},{10,12},{11,12},{12,10},{13,10},{14, 8},{15, 8},
	{16, 6},{17, 6},{18, 4},{19, 4},{20, 0},{21, 0},{22, 2},{23, 2},
	{24,23},{25,23},{26,21},{27,21},{28,19},{29,19},{30,17},{31,17},
	{32,15},{33,15},{34,13},{35,13},{36,11},{37,11},{38, 9},{39, 9},
	{40, 7},{41, 7},{42, 5},{43, 5},{44, 1},{45, 1},{46, 3},{47, 3}
};

const std::map< Int_t, Int_t > lane2layer_lut = {
	{40,22},{39,22},{42,20},{41,20},{44,18},{43,18},{46,16},{45,16},
	{48,14},{47,14},{50,12},{49,12},{52,10},{51,10},{54, 8},{53, 8},
	{38, 6},{55, 6},{36, 4},{37, 4},{32, 0},{35, 0},{34, 2},{33, 2},
	{64,23},{63,23},{66,21},{65,21},{68,19},{67,19},{70,17},{69,17},
	{72,15},{71,15},{74,13},{73,13},{76,11},{75,11},{78, 9},{77, 9},
	{62, 7},{79, 7},{60, 5},{61, 5},{56, 1},{59, 1},{58, 3},{57, 3}
};

const std::map<int,bool> layer2isInv_lut = {
	{ 0, kFALSE}, { 1, kTRUE}, { 2, kFALSE}, { 3, kTRUE},
	{ 4, kFALSE}, { 5, kTRUE}, { 6, kFALSE}, { 7, kTRUE},
	{ 8, kFALSE}, { 9, kTRUE}, {10, kFALSE}, {11, kTRUE},
	{12, kFALSE}, {13, kTRUE}, {14, kFALSE}, {15, kTRUE},
	{16, kFALSE}, {17, kTRUE}, {18, kFALSE}, {19, kTRUE},
	{20, kFALSE}, {21, kTRUE}, {22, kFALSE}, {23, kTRUE}
};

bool IsLeftChip(int lane){
	int layerNr = lane2layer_lut.at(lane);
	bool isInv  = layer2isInv_lut.at(layerNr);
	int chipid = lane2chipid_lut.at(lane);
	bool isOdd;
	if (chipid%2 == 1){ isOdd = kTRUE;}
	else {isOdd = kFALSE;}
	bool isLeft = (bool)(isOdd != isInv);
	return isLeft;
}

Int_t convert_raw_data_and_project( const char* inputfilename = "gps6_E20_spread0.3GeV_halfBox8mmAir_t25.1_nch50_d5_pixelThr82_noise20_stepLength1.root" , const Int_t energy = 20, Int_t event = 25)
{

	std::cout << "-------------------------------" << std::endl;
	std::cout << "-------------------------------" << std::endl;
	std::cout << "Settings as following:" << std::endl;
	std::cout << "energy = " << energy << std::endl;
	std::cout << "event = " << event << std::endl;
	std::cout << "-------------------------------" << std::endl;
	std::cout << "-------------------------------" << std::endl;

	//############################################################
	// open the input root file, tree and branches
	//############################################################
	TFile* fileIn  = new TFile(inputfilename, "read");
	if(fileIn->IsZombie()) return -999;
	TFile *outF = new TFile("gps6_xyproj_hist.root", "recreate");
	TTree *projdata = new TTree("projdata", "data in columns and rows");


	

	TTree* tree = nullptr;
	tree = (TTree*) ((TDirectoryFile*) fileIn->Get("CaloOutputWriter"))->Get("Frames");

	vector<int>* col = new vector<int>();
	vector<int>* row = new vector<int>();
	vector<int>* lane = new vector<int>();




	int hits;
	int bins;
	bins = 0;
	const int ntot = 32*32;		// if you want to change the quantization size, do note to also change projection step (quant_grad) accordingly
	int quantization = 32;
	float quant_grad = 32/1024;
	std::vector<int> x1(ntot);
    std::vector<int> *px1 = &x1;
    projdata->Branch("vars", "std::vector<int>", &px1);

	// make empty arrays for the hitmap
    for (int k = 0; k < quantization; ++k) {
        for (int l = 0; l < quantization; ++l) {
        	int m = k * quantization + l;
            x1[m] = 0;
        }
    }


	tree->SetBranchAddress("nHits",  &hits);
	tree->SetBranchAddress("column", &col);
	tree->SetBranchAddress("row",    &row);
	tree->SetBranchAddress("lane",   &lane);

	for(Int_t i=0; i<20000; i++){ //20000 total events, set lower for testing 
		tree->GetEntry(i);

		printf("\n total number of hits: %i\n\n", hits);

		//############################################################
		// drawing object definition
		//############################################################


		printf("3Dhisthitmap_%i \n",i);


		//############################################################
		// Pixel Loop and conversion
		//############################################################

		int c,r,chip, layer;
		bool isLeft;


		for (int hit = 0; hit < hits; ++hit) // loop over hits
		{
			chip = lane2chipid_lut.at(lane->at(hit));
			layer = chipid2layer_lut.at(chip);
			isLeft = IsLeftChip(lane->at(hit));

			if (isLeft)
			{
				c = col->at(hit);
				r = row->at(hit)+512;
				int m = floor(r*quant_grad) * quantization + floor(c*quant_grad);

				x1[m] ++;
			}
			else // isRight
			{
				c = 1023 - col->at(hit);
				r =  - row->at(hit)-1+512; // shifted by one to avoid overlap in the center
				int m = floor(r*quant_grad) * quantization + floor(c*quant_grad);
				x1[m] ++;
			}
		}

		projdata->Fill();

		for (int k = 0; k < quantization; ++k) {
			for (int l = 0; l < quantization; ++l) {
				int m = k * quantization + l;

				x1[m] = 0;
			}
		}
		}
	outF->Write();


	return 0;
}
