import yaml
from os.path import abspath
from sys import argv, exit
import pandas as pd
from glob import glob
import subprocess

root = '/'.join(abspath(__file__).split('/')[:-2])

############### IN TESTING
# FASTQ location is hardcoded here. Needs to be updated for production.
#searchDir = '/'.join(abspath(argv[1]).split('/')[:-1])
#fastqs=glob('{}/**/*.fastq.gz'.format(searchDir), recursive=True)
###################


if len(argv) < 1:
        exit('\n\tUSAGE: {} <samplesheet.csv> <machine> <runid>\n'.format(__file__))

try:
        machine,runid = argv[2:4]
except (IndexError, ValueError):
        machine,runid = 'testMachine','testRunID'

data = {'runid':runid, 'machine':machine, 'barcodes':{}}
metadata = {}
irma_dict = {'Spike-only':'CoV-s-gene','':'CoV-minion-long-reads','Whole-genome':'CoV-minion-long-reads'}
def reverse_complement(seq):
    rev = {'A':'T','T':'A','C':'G','G':'C',',':','}
    seq = seq[::-1]
    return ''.join(rev[i] for i in seq)

def clarityid_csid_cuid_control(samplesheet_sample_id):
        controls = ['ntc', 'control', 'hec','isolate_rna', 'pcr', 'water','blank','hsc']
        if True in [True for i in controls if i in samplesheet_sample_id.lower()]:
                #if '-' in samplesheet_sample_id:
                return samplesheet_sample_id.split('_')[0], 'control', '_'.join(samplesheet_sample_id.split('_')[1:-2]), samplesheet_sample_id.split('_')[-1]
                #else:
                #        return samplesheet_sample_id.split('_')[0], 'control', '_'.join(samplesheet_sample_id.split('_')[1:])
        else:
                return samplesheet_sample_id.split('_')[0:4444]

df = pd.read_csv(argv[1])
dfd = df.to_dict('index')
failures = ''
try:
    with open('{}/lib/{}.yaml'.format(root, dfd[0]['Barcode_expansion_pack']), 'r') as y:
        barseqs = yaml.safe_load(y)
        #print(barseqs)
except:
    with open('{}/lib/{}.yaml'.format(root, dfd[0]['kit']), 'r') as y:
        barseqs = yaml.safe_load(y)
try:
    plate = dfd[0]['Plate']
except:
    plate = 'NULL'
for d in dfd.values():
    fastq_pass = glob('/scicomp/home-pure/sars2seq/data/by-instrument/'+ machine + '/' + runid + '/no_sample/*' + d['flow_cell_id'] + "*/fastq_pass/*/")
    if d['barcode'] in [x.split("/")[-2] for x in fastq_pass]:
        clarityid, csid, cuid, artifactid = clarityid_csid_cuid_control(d['Alias'])
        data['barcodes'][d['Alias']] = {'clarityid':clarityid,
                                                                        'csid':csid,
                                                                        'cuid':cuid,
                                                                        'Artifactid':artifactid,
                                                                        'Library':d['Library'],
                                                                        'flow_cell_id':d['flow_cell_id'],
                                                                        'flow_cell_product_code':d['flow_cell_product_code'],
                                                                        'kit':d['kit'],
                                                                        'sample_id':d['sample_id'],
                                                                        'experiment_id':d['experiment_id'],
                                                                        #'irma_module':irma_dict[d['Target']],
                                                                        'barcode_number':d['barcode'],
                                                                        'barcode_sequence':barseqs[d['barcode']],
                                                                        'barcode_sequence_rc':reverse_complement(barseqs[d['barcode']])}
        metadata[d['Alias']] = {'clarityid':clarityid,'csid':csid,'cuid':cuid, 'Lane':'1','Sample_ID':d['Alias'], 'Sample_Name':csid+'_'+cuid,'Sample_Plate':plate, 'Sample_Well':d['Sample_Well'], 'Sample_Project':'nanopore', 'index':'NULL', 'I7_Index_ID':d['barcode'],'index2':'NULL', 'I5_Index_ID':'NULL', 'Library':d['Library'],'Artifactid':artifactid,'Project':'nanopore'}
        try:
            data['barcodes'][d['Alias']].update({'irma_module':irma_dict[d['Target']]})
        except:
            data['barcodes'][d['Alias']].update({'irma_module':'CoV-minion-long-reads'})
    else:
        clarityid, csid, cuid, artifactid = clarityid_csid_cuid_control(d['Alias'])
        if 'control' not in csid.lower():
            failures+=d['barcode']+','+csid+"_"+cuid+','+clarityid+'\\n'

#data['header'] = dict(dfd.Header)
#data['samples'] = data['barcodes'][d['Alias']]

metadataDF = pd.DataFrame(metadata).transpose()
with open('samplesheet_metadata.csv', 'w') as out:
        metadataDF.to_csv(out,sep='\t', index=False)
#exit()
with open('config.yaml', 'w') as out:
        yaml.dump(data, out, default_flow_style=False)

if len(failures) > 1:
    fail_script = root + '/scripts/send_failures.sh'
    subprocess.call([fail_script,"-i", failures, "-r", runid, "-a", "qgx6@cdc.gov,nbx0@cdc.gov,ylo1@cdc.gov,fep2@cdc.gov"])
