#!/usr/bin/env python

"""
This is the Python wrapper script for running the command line version of TARGeT. Please see the README for dependencies, installation instructions, and change log. 

From the directory containing TARGeT, run 
python target.py -h
for help.

Brad Cavinder
"""

import os
import os.path
import sys
import datetime
import time
import glob
import subprocess as subp
import multiprocessing as mp
import argparse
import re
import fastaIO
from collections import defaultdict
from distutils.spawn import find_executable

path = sys.path[0]
path = str(path) + "/"
#print "TARGeT path:" + path

#-----------Define functions-----------------------------------------------------

def frange(x, y, jump):
    frange_list = []
    while x < y:
        frange_list.append(x)
        x += jump
        continue
    return frange_list

def frange_convert(frange_list, mode):
    convert_list = []
    for i in frange_list:
        i = str(i)
        if mode == 1:
            i = i[:4]
        elif mode == 2:
            i = i[:5]
        convert_list.append(float(i))
    return convert_list

#setup available floating point options
ident_list1 = frange(0.001, 1, 0.001)
ident_list2 = frange_convert(ident_list1, 2)
ident_list3 = frange(0, 10, 0.01)
ident_list4 = frange_convert(ident_list3, 1)
    

def BLASTN(query, blast_file_out):
    subp.call(["blastall", "-p", "blastn", "-F", "F", "-m", "0", "-d", str(args.genome), "-i", query, "-o", str(blast_file_out) + ".blast", "-e", str(args.b_e), "-b", str(args.b_a), "-v", str(args.b_d), "-a", str(args.P)])

def TBLASTN(query, blast_file_out):
    subp.call(["blastall", "-p", "tblastn", "-F", "F", "-m", "0", "-d", str(args.genome), "-i", query, "-o", str(blast_file_out) + ".blast", "-e", str(args.b_e), "-b", str(args.b_a), "-v", str(args.b_d), "-a", str(args.P)])

def Blast_draw(blast_file_out):
    subp.call(["perl", path + "v3_blast_drawer.pl", "-i", str(blast_file_out) + ".blast", "-o", str(blast_file_out)])

def img_convert(in_file, out_file):
    subp.call(["convert", in_file, out_file])

def PHI(blast_in, PHI_out, query):
    subp.call(["perl", path + "PHI_2.4.pl", "-i", blast_in, "-q", query, "-D", args.genome, "-o", PHI_out, "-e", str(args.p_e), "-M", str(args.p_M), "-P", Type, "-d", str(args.p_d), "-g", str(args.p_g), "-n", str(args.p_n), "-c", str(args.p_c), "-G", str(args.p_G), "-t", str(args.p_t), "-f", str(args.p_f), "-p", args.p_p, "-R", realign])

def PHI_draw(PHI_out, Type):
    subp.call(["perl", path + "PHI_drawer2.pl", "-i", str(PHI_out) + ".list", "-o", str(PHI_out) + ".tcf_drawer", "-m", args.p_t, "-P", Type, "-n", str(600)])

def MAFFT_NT(in_path, out_path):
    subp.call(["mafft", "--ep", "0.15", "--op", "1.2", "--thread",  str(args.P), "--localpair", "--maxiterate",  "16", "--out", out_path, in_path])

def MAFFT_P(in_path, out_path):
    subp.call(["mafft", "--thread",  str(args.P), "--maxiterate",  "100", "--out", out_path, in_path])

def runTarget(query, blast_out, blast_file_out, path):
    #make output directory
    os.mkdir(blast_out)
    
    #make command log file
    log_out = open(os.path.join(blast_out, "log.txt"), "w")
    print>>log_out, " ".join(sys.argv)
    log_out.close()
    
    #use blastn if DNA
    if args.Type == 'nucl':
        print "Using BLASTN\n"
        BLASTN(query, blast_file_out)
        
    #use tblastn if protein
    elif args.Type == 'prot':
        print "Using TBLASTN\n"
        TBLASTN(query, blast_file_out)
        
    #make svg drawing(s)
    print "Making svg image of blast results\n"
    Blast_draw(blast_file_out)

    #convert svg image to jpg
    print "Converting svg to jpg\n"
    for svg_file in glob.glob(str(blast_file_out) + "*.svg"): 
        jpg_file = os.path.splitext(svg_file)[0]
        jpg_file = jpg_file + ".jpg"
        img_convert(svg_file, jpg_file)
        
    if args.S == 'Blast':
        return
    
    blast_in = str(blast_file_out) + ".blast"
    PHI_out = str(blast_file_out)
    print "Blast in:", blast_in + "  PHI out:", PHI_out
    print "Running PHI"
    PHI(blast_in, PHI_out, query)
    print "PHI finished!\n"
    
    filter_list = str(blast_file_out) + ".list"
    #print "filter list path:", filter_list
    filter_path = os.path.join(path, "parse_target_list.py")
    #print "filter script path:", filter_path
    
    #print args.E
    if args.E == True:
        #print "E is true!"
        subp.call(["cp", filter_list, filter_list + "_ori.list"])
        subp.call(["python", filter_path, filter_list, str(args.W)])
        time.sleep(1)
        PHI_draw(filter_list + "_ori", Type)
        img_convert(filter_list + "_ori" + ".tcf_drawer.svg", filter_list + "_ori" + ".tcf_drawer.pdf")
    
    #make svg image of PHI homologs
    print "Making svg image of homologs\n"
    PHI_draw(PHI_out, Type)

    #convert svg to pdf
    print "Coverting svg image to pdf\n"
    img_convert(str(PHI_out) + ".tcf_drawer.svg", str(PHI_out) + ".tcf_drawer.pdf")

    #get query length
    query_in = open(query, "r")
    query_len = 0
    for title, seq in fastaIO.FastaGeneralIterator(query_in):
        query_len = len(seq)
    query_in.close()
    
    #check that two or more copies were found and setup index checker to check for correct length flanks and for the correct locus sequence
    print "Building index dict"
    copies = 0
    index_dict = defaultdict(dict)
    dna_copies_in = open(PHI_out + ".dna", "r")
    for title, seq in fastaIO.FastaGeneralIterator(dna_copies_in):
        #print "Seq_name:", title, "\nSeq_len:", len(seq), "\n"
        index_dict[title]['left'] = seq[:25].upper()
        index_dict[title]['right'] = seq[-25:].upper()
    dna_copies_in.close()
    flank_file_path = PHI_out + ".flank"
    
    genome_dict = {}
    genome_in = open(str(args.genome), "r")
    for title, seq in fastaIO.FastaGeneralIterator(genome_in):
        title2 = title.split(" ")[0]
        genome_dict[title2] = seq
    genome_in.close()
    
    flank_file_path = standardize_flanks(flank_file_path, index_dict, args.p_f, genome_dict)
    
    flank_copies_in = open(flank_file_path, "r")
    for title, seq in fastaIO.FastaGeneralIterator(flank_copies_in):
        copies+=1
    flank_copies_in.close()
    
    if args.S == 'PHI':
        return
    
    if copies >= 2: 
        filter_list = []
        in_list = []
        if args.a == 'hits' or args.a == 'both':
            print "hits will be aligned"
            if args.f > 0:
                print "Filtering flagged for hits\n"
                if args.Type == 'nucl':
                    filter_list.append([PHI_out + ".dna", PHI_out + ".dna_filter-" + str(args.f)])
                else:
                    in_list.append(str(PHI_out) + ".aa")
            else:
                if args.Type == 'nucl':
                    in_list.append(str(PHI_out) + ".dna")
                else:
                    in_list.append(str(PHI_out) + ".aa")

        if args.a == 'flanks' or args.a == 'both':
            print "Flanks will be aligned"
            if args.f > 0:
                print "Filtering flagged for flanks\n"
                if args.Type == 'nucl':
                    filter_list.append([flank_file_path, PHI_out + ".flank_filter-" + str(args.f)])
                else:
                    in_list.append(flank_file_path)
            else:
                in_list.append(flank_file_path)
        print "Entries in filter list:  ", len(filter_list), "\n"
        if len(filter_list) != 0:
            #print "in_list =\n", in_list
            for in_path, out_path_base in filter_list:
                in_file = open(in_path, "r")
                out_path = out_path_base + "_under"
                out_path2 = out_path_base + "_over"
                out_file = open(out_path, "w")
                out_file2 = open(out_path2, "w")
                for title, seq in fastaIO.FastaGeneralIterator(in_file):
                    copy_len = len(seq) - (int(args.p_f) * 2)
                    if copy_len <= (query_len * args.f):
                        print>>out_file, ">" + title + "\n" + seq
                    else:
                        print>>out_file2, ">" + title + "\n" + seq
                in_list.append(out_path)
                in_file.close()
                out_file.close()
                out_file2.close()

        #Run Mafft
        
        in_count = len(in_list)
        processed = 0
        for in_path in in_list:
            split_list = []
            in_file = open(in_path, "r")
            copies = 0            
            for title, seq in fastaIO.FastaGeneralIterator(in_file):
                copies += 1
            in_file.close()
            print str(copies) + " copies in " + in_path, "\n"
            if copies >= 601:
                print "Shuffling and splitting file for seperate alignments\n"
                split_list, copies = fastaIO.shuffle_split(in_path, 350)
                print "Length of split list in:", len(split_list)
            print "Length of split list out:", len(split_list)
            if len(split_list) > 0:
                for path in split_list:
                    msa_out = path + ".msa"
                    print "Running Mafft"
                    if args.Type == 'nucl':
                        MAFFT_NT(path, msa_out)
                    else:
                        MAFFT_P(path, msa_out)
                    if not os.path.exists(msa_out):
                        print "MAFFT alignment failed and is most likely because of not enough RAM. Please rerun TARGeT on this query with increased RAM and/or fewer processors. TARGeT is now exiting."
                        exit(1)
                processed += 1
                if args.S == 'MSA':
                    if (in_count - processed) == 0:
                        return
                    else:
                        continue
                    
            else:
                msa_out = in_path + ".msa"
                print "Running Mafft"
                if args.Type == 'nucl':
                    MAFFT_NT(in_path, msa_out)
                else:
                    MAFFT_P(in_path, msa_out)
                processed += 1
                
                if not os.path.exists(msa_out):
                    print "MAFFT alignment failed and is most likely because of not enough RAM. Please rerun TARGeT on this query with increased RAM and/or fewer processors. TARGeT is now exiting."
                    exit(1)
                #print "in_count - processed = ", in_count - processed, "\n"
                if args.S == 'MSA':
                    if (in_count - processed) == 0:
                        return
                    else:
                        continue
                
                
            #Run FastTreeMP
            
            msa_list = glob.glob(in_path + "*.msa")
            print "FastTreeMP will run on", len(msa_list), " MSA(s)\n"
            c = 0 
            for msa_out in msa_list:
                print "Running FastTreeMP on MSA", c
                tree_out = msa_out + ".nw"
                print "Output tree path: ", tree_out, "\n\n"
            
                #Can only limit FastTree processor use through OMP_NUM_THREADS. Otherwise, it will use all processors available.
                current_env = os.environ.copy()
                #print "current_env before change:  ", current_env
                current_env['OMP_NUM_THREADS'] = str(args.P)
                #print "OMP_NUM_THREADS after change:  ", current_env['OMP_NUM_THREADS'], "\n\n"

            
                if args.Type == 'nucl' or (args.Type == 'prot' and ".flank" in msa_out):
                    proc = subp.Popen(["FastTreeMP", "-nt", "-gamma", "-out", tree_out, msa_out], env = current_env)
                    proc.wait()
                    print "\nFastTreeMP finished.\n"
                else:
                    proc = subp.Popen(["FastTreeMP", "-gamma", "-out", tree_out, msa_out], env = current_env)
                    proc.wait()
                    print "\nFastTreeMP finished.\n"

                print "Converting output tree file to eps image\n"
                out = open(tree_out + ".eps", "w") #open output file for redirected stdout
                #print "Eps image out path: ", out
            
                if copies > 45:
                    height = copies * 13
                    width = round(height/3)
                    print "Image height: ", height, "\twidth: ", width, "\n"
                    subp.call(["treebest",  "export", "-y", str(height), "-x", str(width), "-b", "4.5", "-f", "13", "-m", "40", tree_out], stdout=out)
                else:
                    subp.call(["treebest",  "export", tree_out], stdout=out)
                out.close() #close output file

                print "Coverting eps image to pdf\n"
                subp.call(["convert", tree_out + ".eps", tree_out + ".pdf"])
                c += 1
    else:
        print "Less than two copies found. Multiple alignment and tree building will not be performed.\n"
        
def runTarget_expander(args):
    return runTarget(*args)

def runMpTarget(file_list):
    #counter to keep track of the number of files that have been processed
    p = 0
    count = len(file_list)
    print count, " files to be processed"

    #Run pipeline on each file with it's own output directory in the main output directory
    query_parameters = []
    for fasta in file_list:
        print "Query:", fasta
        filename = os.path.splitext(fasta)[0]
        file_name = os.path.split(filename)[1]
        #set output directory
        blast_out = os.path.normpath(os.path.join(out_dir, file_name))
        
        #set output filename
        blast_file_out = os.path.join(blast_out, file_name)
        query_parameters.append([fasta, blast_out, blast_file_out, path])
    
    pool = mp.Pool(args.T)
    target_map = pool.map(runTarget_expander, query_parameters)
    for target_x in target_map:
        p += 1
        print "TARGeT has processed ", p, " of ", count, " subfiles"
    
def standardize_flanks(flank_file_path, index_dict, flank, genome_dict2):
    """Find the index position of the start and end of the DNA match in the sequences with flanks. If either flank is not as long as the flank setting, add N's to reach that number. If the index is -1 (not found), go back into the genome sequence to get the correct locus"""
    
    seq_dict = {}
    seq_order = []
    modified = 0
    flank_in = open(flank_file_path, "r")
    adj_flank_path = flank_file_path + "_adj"
    print "In standardize_flanks, flank =", flank
    base_path = os.path.splitext(flank_file_path)[0]
    genomic_path = base_path + ".genomic"
    genomic_out = open(genomic_path, "w")
    
    for title, seq in fastaIO.FastaGeneralIterator(flank_in):
        add_left = ''
        add_right = ''
        title = title.strip()
        seq_order.append(title)
        seq_dict[title] = seq
        strand = title.split("Direction:")[1]
        strand = strand.strip()
        seq_len = len(seq)
        contig = title.split("Sbjct:")[1].split(" ")[0]
        locus_str = title.split("Location:(")[1].split(" - ")
        start = int(locus_str[0])
        end = int(locus_str[1].split(")")[0])
        name = title
        #get genomic copy without flanks as PHI only report hit seq not genomic, then proceed
        genomic_seq = fastaIO.sequence_retriever( contig, start, end, 0, genome_dict2)
        if strand == 'minus':
            genomic_seq = fastaIO.reverse_complement(genomic_seq)
        print>>genomic_out, ">" + title + "\n" + genomic_seq
        
        if args.Type == 'nucl':
            name = title.split(' ')[0]
        if not seq_len or seq_len == 0:
            left_flank_len = -1
            right_flank_index = -1
        else:    
            left_flank_len = seq.upper().find(index_dict[name]['left'])
            if left_flank_len < flank and left_flank_len != -1:
                retry = seq.upper().find(index_dict[name]['left'], flank-20)
                if retry == flank:
                    left_flank_len = retry
            
            right_flank_index = seq.upper().rfind(index_dict[name]['right']) 
            right_flank_start = right_flank_index + 25 #first nt of flank, 1st nt after search string
            if right_flank_start > (seq_len - flank) and right_flank_index != -1:
                retry = seq.upper().rfind(index_dict[name]['right'], 0, (seq_len - flank)+20)
                if retry == (seq_len - flank):
                    right_flank_start = retry + 25
        
        if left_flank_len == -1 or right_flank_index == -1:
            new_seq = fastaIO.sequence_retriever(contig, start, end, flank, genome_dict2)
            if strand == 'minus':
                new_seq = fastaIO.reverse_complement(new_seq)
            seq_dict[title] = new_seq
            modified += 1
            continue
        right_flank_len = seq_len - right_flank_start
        if left_flank_len < flank:
            needed_left = flank - left_flank_len
            add_left = "N" * needed_left
        if right_flank_len < flank:
            needed_right = flank - right_flank_len
            add_right = "N" * needed_right
        if add_left or add_right:
            new_seq = add_left + seq + add_right
            seq_dict[title] = new_seq
            modified += 1
    flank_in.close()
    genomic_out.close()
    if modified != 0:
        flank_out = open(adj_flank_path, "w")
        for title in seq_order:
            print>>flank_out, ">" + title + "\n" + seq_dict[title]
        flank_out.close()
        return(adj_flank_path)
    else:
        return(flank_file_path)

#-----------Make command line argument parser------------------------------------

parser = argparse.ArgumentParser(prog='target.py', formatter_class=argparse.ArgumentDefaultsHelpFormatter, description="This is the command line implementation of TARGeT: Tree Analysis of Related Genes and Transposons (http://target.iplantcollaborative.org/). Please read the README file for program dependencies.")

input_group = parser.add_mutually_exclusive_group(required=True)

input_group.add_argument("-q", metavar="Input file", help="Path to single input query sequence file (may contain multiple sequences of the same type [DNA or protein]).")

input_group.add_argument("-d", metavar="Input directory", help="Path to input directory with multiple query sequence files (each may contain multiple sequences). All sequences must be of the same type (DNA or protein). The directory can not contain non-query files.")

parser.add_argument("-t", dest="Type", metavar="Search type", choices=("nucl", "prot"), default="prot", help="Type of input query sequence(s): DNA = 'nucl'  protein = 'prot'")

parser.add_argument("genome", metavar="Genome_sequence_file", help="Path of the genome sequence file to be searched (or other sequence to be searched).")

parser.add_argument("Run_Name", help="Name for overall run")

parser.add_argument("-o", metavar="Output path", default="Current working directory", help="Path to an existing directory for output. A subdirectory for the run will be created with further subdirectories containing the output files for each search sequence.")

parser.add_argument("-i", metavar="Input query type", choices=("s", "mi", "g"), default="s", help="Number of input queries per file(s): s = single query sequence, mi = multiple individual query sequences, g = FASTA multiple sequence alignment or list of sequences; All input files/sequences must be the same type of sequence as set by -t.")

parser.add_argument("-a", metavar="Alignments to perform", choices=("hits", "flanks", "both"), default="hits", help="Input sequences for multiple sequence alignent: hits = each copy only contains sequence that matches the query (recomended for most protein queries), flanks = each copy contains the sequences that matches the query plus flanking sequence on each side of the match for which the length is set by -p_f ")

parser.add_argument("-f", metavar="Filter length (query length * X)", type=float, default=0, choices=ident_list4, help="Multiple of query length used as maximum length of copies to be included in the multiple sequence alignment(s). Valid values are: 0-10 by 0.01 increments. Default of 0 means no filtering. Values between 0 and 1 return copies smaller than the input query sequence.")

parser.add_argument("-P", metavar="Processors", type=int, default=1, help="The number of processors to use for Blast, Mafft, and FastTree steps. All other steps use 1 processor. The programs are not multi-node ready, so the number of processors is limited to that available to one computer/node.")

parser.add_argument("-T", metavar="Threads", type=int, default=1, help="Use multiple threads to run multiple query searches in parallel. This will only be useful if using either option -d or option -q with option -i = mi. If -T is set, the total number of cpus that will be used by your run will be P*T, i.e. if -P 4 and -T 4, then 16 cpus will be used.")

parser.add_argument("-E", action='store_true', default="False", help="Require hits to match the ends of the query sequence. The -W flag modifies the distance from the ends a hit can be and satisfy this flag. Using this flag alone is equivalent to '-E -W 0'.")

parser.add_argument("-W", metavar="Window size", type=int, default=0, help="Maximum distance away from query ends for a hit to be considered matching the ends. Only used if the -E flag is set. The default value of 0 requires a hit to start and stop at the first and last characters of the query. A value of 4 would consider hits starting within the first 5 and ending within the last 5 characters of the query as matches to the ends.")

parser.add_argument("-S", metavar="Stopping point", type=str, choices=("Blast", "PHI", "MSA", "Tree"), default="Tree", help="The stage, after completion, to stop the program. By default, all stages (Blast, PHI, MSA, Tree) are run. For example if you want to stop the program after Blast and PHI, exiting before the MSA stage, enter PHI.")

parser.add_argument("-DB", action='store_false', default="True", help="Skip formatDB and custom indexing. These steps are required for the first search against a genome. If the genome sequence file is changed in any way, these steps will need to be performed again. Otherwise, you may use this flag to skip these steps. By default, the steps are always performed")

parser.add_argument("-v", action='version', version='TARGeT-2.10', help="Version information")

#BLAST arguments
parser_blast = parser.add_argument_group("BLAST")

parser_blast.add_argument("-b_e", metavar="BLAST E-value", default="0.001", type=float, help="Maximum Expect value to include a match in the BLAST results")

parser_blast.add_argument("-b_a", metavar="# alignments", default="500", type=int, help="The maximum number of hit alignments to include per query sequence.")

parser_blast.add_argument("-b_d", metavar="# descriptions", default="100", help="The maximum number of descriptions of hits included in BLAST output per query sequence.")


#PHI arguments
parser_phi = parser.add_argument_group("PHI")

parser_phi.add_argument("-p_e", metavar="PHI E-value", default="0.01", type=float, help="Maximum Expect value for PHI.")

parser_phi.add_argument("-p_M", metavar="Minimum query match", type=float, default=0.7, choices=ident_list2, help="Minimum decimal fraction of match length.")

parser_phi.add_argument("-p_d", metavar="Max intron length", default="8000", type=int, help="Maximum intron length.")

parser_phi.add_argument("-p_g", metavar="Min intron length", type=int, default=10, help="Minimum intron length.")

parser_phi.add_argument("-p_n", metavar="Max copies", type=int, default=100, help="Maximum number of homolgs in output.")

parser_phi.add_argument("-p_R", action='store_true', help="Perform realignments to find small exons.")

parser_phi.add_argument("-p_c", metavar="Composition stats", default="0", choices=('0', '1', '2', '3'), help="Use composition-based statistics during realignment. 0 = off, 1 = use 2001-based stats, 2 = use 2005-based stats conditioned on sequence properties, 3 = use 2005-based stats unconditionally. See BLAST2 help, man page, or web resources for further explanation.")

parser_phi.add_argument("-p_G", metavar="Add GenBank accession #", default="0", choices=('0', '1'), help="Add GenBank accession numbers. Use only if genome being searched is in GenBank format. 0 = no, 1 = yes.")

parser_phi.add_argument("-p_t", metavar="Substitution matrix", default="62", choices=('50', '62', '80'), help="Substitution matrix used to score alignments. 50 = BLOSUM50, 62 = BLOSUM62, 80 = BLOSUM80. DNA queries will automatically use an identity matrix.")

parser_phi.add_argument("-p_f", metavar="Flanking sequence", type=int, default=100, help="Length of flanking sequences to be included.")

parser_phi.add_argument("-p_p", action='store_true', help="Filter out psuedogenes (matches with internal stop codons).")


#-----------Parse command line input---------------------------------------------

args = parser.parse_args()

#print args
#change arguments to usable forms or make new assignment
realign = '0'
#print "realign before = ", realign
if args.Type == 'prot':
    Type = '1'
elif args.Type == 'nucl':
    Type = '0'
args.p_t = path + 'BLOSUM' + str(args.p_t) + '.txt'
if args.p_R == 1:
    realign = '1'
if args.p_p == 'True':
    args.p_p = '1'
else:
    args.p_p = '0'

#-----------Check for executables & genome file----------------------------------

error_message = ''
error_start = "The following programs were not found in your $PATH:"
error_end = "Please install any missing programs and rerun TARGeT."

blastall_exe = find_executable("blastall")
perl_exe = find_executable("perl")
convert_exe = find_executable("convert")
mafft_exe = find_executable("mafft")
FastTreeMP_exe = find_executable("FastTreeMP")
treebest_exe = find_executable("treebest")

if blastall_exe is None:
    error_message = error_start + "\n\tblastall (NCBI BLAST2  v2.2.26)"
if perl_exe is None:
    if error_message == '':
        error_message = error_start + "\n\tPerl"
    else:
        error_message += "\n\tPerl"
if convert_exe is None:
    if error_message == '':
        error_message = error_start + "\n\tImageMagick"
    else:
        error_message += "\n\tImageMagick"
if mafft_exe is None:
    if error_message == '':
        error_message = error_start + "\n\tMAFFT"
    else:
        error_message += "\n\tMAFFT"
if FastTreeMP_exe is None:
    if error_message == '':
        error_message = error_start + "\n\tFastTreeMP"
    else:
        error_message += "\n\tFastTreeMP"
if treebest_exe is None:
    if error_message == '':
        error_message = error_start + "\n\tTreeBest"
    else:
        error_message += "\n\tTreeBest"

if error_message == '':
    print "\nAll required programs located."
else:
    error_message += error_end
    print error_message
    sys.exit(-1)

try:
    with open(args.genome, "r") as test:
        pass
except:
    print "\nGenome file could not be located at", args.genome, "\n"
    raise

#-----------Create main output directory-----------------------------------------

if args.o != "Current working directory":
    if args.o[-1] != "/":
        args.o = args.o + "/"
else:
    args.o = ""
#make the main output directory using current date and time
now = datetime.datetime.now()


if args.q and args.i == 's' or args.i == 'g':
    query_no_ext = os.path.splitext(args.q)[0]
    basedir, query_name = os.path.split(query_no_ext)
    out_dir = args.o + args.Run_Name + "_" + query_name + "_" + now.strftime("%Y_%m_%d_%H%M%S")
else:
    out_dir = args.o + args.Run_Name + "_" + now.strftime("%Y_%m_%d_%H%M%S")
    try:
        os.mkdir(out_dir)
    except:
        pass


#-----------Make BLAST database & Run custom indexer-----------------------------
if args.DB:
    print "\nRunning formatdb\n"
    subp.call(["formatdb", "-i", args.genome,"-p", "F", "-o", "T", "-n", args.genome])
    print "Running custom indexer\n"
    subp.call(["perl", path + "reads_indexer.pl", "-i", args.genome])
else:
    print "\n", args.genome

#-----------Single input file----------------------------------------------------

#for single indiviual query or grouped query
if args.q and args.i == 's' or args.i == 'g':
    print "Single input file, single or group input\n"
    query = args.q
    try:
        with open(query, "r") as test:
            pass
    except:
        print "Query file could not be located at", query
        raise
    
    #set output filename
    blast_file_out = os.path.join(out_dir, query_name)
    runTarget(query, out_dir, blast_file_out, path)
    print "TARGeT has finished!"


#for multiple individual queries-------------------------------------------------
elif args.q and args.i == 'mi':
    print "Single input file, multiple individual inputs.\n"
    
    new_files = []
    base_path, base_file = os.path.split(args.q)
    base_file = os.path.splitext(base_file)[0]
    c = 1
    try:
        in_handle = open(args.q, "r")
    except:
        print "Query file could not be located at", args.q, "\n"
        raise
    for title, seq in fastaIO.FastaTitleStandardization(in_handle):
        seq_path = os.path.join(base_path, title + "_split" + str(c) + ".fa")
        new_files.append(seq_path)
        out_handle = open(seq_path, "w")
        print>>out_handle, ">" + title, "\n", seq
        c += 1
        out_handle.close()
    in_handle.close()
    
    runMpTarget(new_files)
    for item in new_files:
        os.unlink(item)
    print "TARGeT has finished!"

#-----------Directory input------------------------------------------------------

#for single individual queries
elif args.d and args.i == 's' or args.i == 'g':
    print "Directory input, each file has a single or group query.\n"
    files = os.listdir(args.d) #get all files in the directory
    runMpTarget(files)
    for item in files:
        os.unlink(item)
    print "TARGeT has finished!"

#for multiple individual queries-------------------------------------------------
elif args.d and args.i == 'mi':
    print "Directory input, each file has multiple individual queries.\n"
    
    files = os.listdir(args.d) #get all files in the directory

    #count the number of input files
    count = 0
    for f in files:
        count += 1
        print f        
    print count, " files to be processed"

    #counter to keep track of the number of files that have been processed
    p = 0
    
    for f in files:
        #setup name for output subdirectory for pre-split file
        base_dir = os.path.normpath(os.path.join(out_dir, os.path.splitext(f)[0]))
        os.mkdir(base_dir)

        #setup full path to fasta file for splitting
        in_full = os.path.normpath(os.path.join(args.d, f))

        new_files = []
        in_handle = open(in_full, "r")
        for title, seq in fastaIO.FastaTitleStandardization(in_handle):
            seq_path = os.path.join(base_dir, title + "_split" + str(c) + ".fa")
            out_handle = open(seq_path, "w")
            new_files.append(seq_path)
            print>>out_handle, ">" + title, "\n", seq
            out_handle.close()
        in_handle.close()
        
        runMpTarget(new_files)
        for item in new_files:
            os.unlink(item)
        
        print "TARGeT has fully processed ", p, " of ", count, " files"
    print "TARGeT has finished!"
