import pandas as pd
import numpy
import json
from sys import argv, path, exit, executable
import os.path as op
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from dash import html
import yaml

path.append(op.dirname(op.realpath(__file__)))
import irma2pandas  # type: ignore
import dais2pandas  # type: ignore

try:
    irma_path, samplesheet, platform, virus = argv[1], argv[2], argv[3], argv[4]
except IndexError:
    exit(
        f"\n\tUSAGE: python {__file__} <path/to/irma/results/> <samplesheet> <ont|illumina> <flu|sc2>\n"
        f"\n\t\t*Inside path/to/irma/results should be the individual samples-irma-dir results\n"
        f"\n\tYou entered:\n\t{executable} {' '.join(argv)}\n\n"
    )

# Load qc config:
with open(
    op.dirname(op.dirname(op.realpath(__file__))) + "/irma_config/qc_pass_fail_settings.yaml"
) as y:
    qc_values = yaml.safe_load(y)

proteins = {
    "sc2": "ORF10 S orf1ab ORF6 ORF8 ORF7a M N ORF3a E",
    "flu": "PB1-F2 HA M1 NP HA1 BM2 NB PB2 NEP PB1 HA-signal PA-X NS1 M2 NA PA",
}
ref_proteins = {
    "ORF10": "SARS-CoV-2",
    "S": "SARS-CoV-2",
    "orf1ab": "SARS-CoV-2",
    "ORF6": "SARS-CoV-2",
    "ORF8": "SARS-CoV-2",
    "ORF7a": "SARS-CoV-2",
    "M": "SARS-CoV-2",
    "N": "SARS-CoV-2",
    "ORF3a": "SARS-CoV-2",
    "E": "SARS-CoV-2",
    "SARS-CoV-2": "SARS-CoV-2",
    "PB1-F2": "A_PB1 B_PB1",
    "HA": "A_HA_H10 A_HA_H11 A_HA_H12 A_HA_H13 A_HA_H14 A_HA_H15 A_HA_H16 A_HA_H1 \
        A_HA_H2 A_HA_H3 A_HA_H4 A_HA_H5 A_HA_H6 A_HA_H7 A_HA_H8 A_HA_H9 B_HA",
    "M1": "A_MP B_MP",
    "NP": "A_NP B_NP",
    "HA1": "A_HA_H10 A_HA_H11 A_HA_H12 A_HA_H13 A_HA_H14 A_HA_H15 A_HA_H16 A_HA_H1 \
        A_HA_H2 A_HA_H3 A_HA_H4 A_HA_H5 A_HA_H6 A_HA_H7 A_HA_H8 A_HA_H9 B_HA",
    "BM2": "B_MP",
    "NB": "B_MP",
    "PB2": "A_PB2 B_PB2",
    "NEP": "A_NS B_NS",
    "PB1": "A_PB1 B_PB1",
    "HA-signal": "A_HA_H10 A_HA_H11 A_HA_H12 A_HA_H13 A_HA_H14 A_HA_H15 A_HA_H16 A_HA_H1 \
        A_HA_H2 A_HA_H3 A_HA_H4 A_HA_H5 A_HA_H6 A_HA_H7 A_HA_H8 A_HA_H9 B_HA",
    "PA-X": "A_PA B_PA",
    "NS1": "A_NS B_NS",
    "NS": "A_NS B_NS",
    "M2": "A_MP B_MP",
    "M": "A_MP B_MP",
    "NA": "A_NA_N1 A_NA_N2 A_NA_N3 A_NA_N4 A_NA_N5 A_NA_N6 A_NA_N7 A_NA_N8 A_NA_N9 B_NA",
    "PA": "A_PA B_PA",
}

###############################################################
## Dataframes
###############################################################

def negative_qc_statement(irma_reads_df, negative_list=""):
    if negative_list == "":
        sample_list = list(irma_reads_df["Sample"].unique())
        negative_list = [i for i in sample_list if "PCR" in i]
    irma_reads_df = irma_reads_df.pivot("Sample", columns="Record", values="Reads").fillna(0)
    if "3-altmatch" in irma_reads_df.columns:
        irma_reads_df["Percent Mapping"] = (
            irma_reads_df["3-match"] + irma_reads_df["3-altmatch"]
        ) / irma_reads_df["1-initial"]
    else:
        irma_reads_df["Percent Mapping"] = (
            irma_reads_df["3-match"] / irma_reads_df["1-initial"]
        )
    irma_reads_df = irma_reads_df.fillna(0)
    statement_dic = {"passes QC": {}, "FAILS QC": {}}
    for s in negative_list:
        try:
            reads_mapping = irma_reads_df.loc[s, "Percent Mapping"] * 100
        except KeyError:
            reads_mapping = 0
        if reads_mapping >= 0.01:
            statement_dic["FAILS QC"][s] = f"{reads_mapping:.2f}"
        else:
            statement_dic["passes QC"][s] = f"{reads_mapping:.2f}"
    return statement_dic


def which_ref(sample, protein, ref_protein_dic, irma_summary_df):
    try:
        return list(
            set(
                irma_summary_df[irma_summary_df["Sample"] == sample]["Reference"]
            ).intersection(set(ref_protein_dic[protein].split()))
        )[0]
    except IndexError:
        print(
            f"no match found for either sample=={sample} in irma_summary_df\n or protein=={protein} in ref_proteins"
        )
    except ValueError:
        return numpy.nan

def pass_qc(reason, sequence):
    reason, sequence = str(reason), str(sequence)
    if reason == 'nan' and sequence != 'nan':
        return 'Pass'
    elif reason == 'nan' and sequence == 'nan':
        return 'No matching reads'
    else:
        return reason

def anyref(ref):
    if ref == '':
        return 'Any'
    else:
        return ref

def failedall(combined_df):
    try:
        for i in combined.index:
            if str(combined.loc[i]['']) != 'nan':
                combined_df.loc[i] = 'No assembly'
    except:
        pass
    return combined_df

def pass_fail_qc_df(irma_summary_df, dais_vars_df, nt_seqs_df):
    if not qc_values[platform]["allow_stop_codons"]:
        pre_stop_df = dais_vars_df[dais_vars_df["AA Variants"].str.contains("[0-9]\*")][
            ["Sample", "Protein"]
        ]
    else:
        pre_stop_df = pd.DataFrame(columns=["Sample", "Protein"])
    pre_stop_df["Reason_a"] = "Premature stop codon"
    if virus == "flu":
        pre_stop_df["Sample"] = pre_stop_df["Sample"].str[:-2]
    try:
        pre_stop_df["Reference"] = pre_stop_df.apply(
            lambda x: which_ref(x["Sample"], x["Protein"], ref_proteins, irma_summary_df),
            axis=1,
        )
    except ValueError:
        pre_stop_df = pd.DataFrame(columns=["Sample", "Protein", "Reference", "Reason_a"])
    ref_covered_df = irma_summary_df[
        (
            irma_summary_df["% Reference Covered"]
            < qc_values[platform]["perc_ref_covered"]
        )
    ][["Sample", "Reference"]]
    ref_covered_df[
        "Reason_b"
    ] = f"Less than {qc_values[platform]['perc_ref_covered']}% of reference covered"
    mean_cov_df = irma_summary_df[
        (irma_summary_df["Mean Coverage"] < qc_values[platform]["mean_cov"])
    ][["Sample", "Reference"]]
    mean_cov_df["Reason_c"] = f"Mean coverage < {qc_values[platform]['mean_cov']}"
    minor_vars_df = irma_summary_df[
        (
            irma_summary_df["Count of Minor SNVs >= 0.05"]
            > qc_values[platform]["minor_vars"]
        )
    ][["Sample", "Reference"]]
    minor_vars_df[
        "Reason_d"
    ] = f"Count of minor variants at or over 5% > {qc_values[platform]['minor_vars']}"
    combined = ref_covered_df.merge(
        mean_cov_df, how="outer", on=["Sample", "Reference"]
    )
    combined = combined.merge(minor_vars_df, how="outer", on=["Sample", "Reference"])
    combined = combined.merge(pre_stop_df, how="outer", on=["Sample", "Reference"])
    combined["Reasons"] = (
        combined[["Reason_a", "Reason_b", "Reason_c", "Reason_d"]]
        .fillna('')
        .agg("; ".join, axis=1)
    )
    # Add in found sequences
    combined = combined.merge(nt_seqs_df, how="outer", on=["Sample", "Reference"])
    combined["Reasons"] = combined.apply(lambda x: pass_qc(x['Reasons'], x['Sequence']), axis=1)
    combined = combined[["Sample", "Reference", "Reasons"]]
    try:
        combined["Reasons"] = (
            combined["Reasons"]
            .replace("^ \+;|(?<![a-zA_Z0-9]) ;|; \+$", "", regex=True)
            .str.strip()
            .replace("^; *| *;$", "", regex=True)
        )
    except AttributeError:
        combined["Reasons"] = combined["Reasons"].fillna("Too few reads matching reference")
    #combined = combined.merge(
    #    irma_summary_df["Sample"], how="outer", on="Sample"
    #).drop_duplicates()
    #combined['Reference'] = combined['Reference'].apply(lambda x: anyref(x))
    combined = (
        combined.drop_duplicates().pivot(index="Sample", columns="Reference", values="Reasons")
        #.drop(numpy.nan, axis=1)
    )
    combined = combined.apply(lambda x: failedall(x))
    try:
        combined = combined.drop(columns='')
    except KeyError:
        pass
    return combined


def irma_summary(
    irma_path, samplesheet, reads_df, indels_df, alleles_df, coverage_df, ref_lens
):
    ss_df = pd.read_csv(samplesheet)
    allsamples_df = ss_df[['Sample ID']].rename(columns={'Sample ID':'Sample'})
    neg_controls = list(ss_df[ss_df["Sample Type"] == "- Control"]["Sample ID"])
    qc_statement = negative_qc_statement(reads_df, neg_controls)
    with open(f"{irma_path}/qc_statement.json", "w") as out:
        json.dump(qc_statement, out)
    reads_df = (
        reads_df[reads_df["Record"].str.contains("^1|^2-p|^4")]
        .pivot("Sample", columns="Record", values="Reads")
        .reset_index()
        .melt(id_vars=["Sample", "1-initial", "2-passQC"])
        .rename(
            columns={
                "1-initial": "Total Reads",
                "2-passQC": "Pass QC",
                "Record": "Reference",
                "value": "Reads Mapped",
            }
        )
    )
    reads_df = reads_df[~reads_df["Reads Mapped"].isnull()]
    reads_df["Reference"] = reads_df["Reference"].map(lambda x: x[2:])
    # reads_df[["Total Reads", "Pass QC", "Reads Mapped"]] = (
    #    reads_df[["Total Reads", "Pass QC", "Reads Mapped"]]
    #    .applymap(lambda x: f"{x:,d}")
    #    .astype("int")
    # )
    reads_df = reads_df[
        ["Sample", "Total Reads", "Pass QC", "Reads Mapped", "Reference"]
    ]
    indels_df = (
        indels_df[indels_df["Frequency"] >= 0.05]
        .groupby(["Sample", "Reference"])
        .agg({"Sample": "count"})
        .rename(columns={"Sample": "Count of Minor Indels >= 0.05"})
        .reset_index()
    )
    alleles_df = (
        alleles_df[alleles_df["Minority Frequency"] >= 0.05]
        .groupby(["Sample", "Reference"])
        .agg({"Sample": "count"})
        .rename(columns={"Sample": "Count of Minor SNVs >= 0.05"})
        .reset_index()
    )
    cov_ref_lens = (
        coverage_df[~coverage_df["Consensus"].isin(["-", "N", "a", "c", "t", "g"])]
        .groupby(["Sample", "Reference_Name"])
        .agg({"Sample": "count"})
        .rename(columns={"Sample": "maplen"})
        .reset_index()
    )
    def perc_len(maplen, ref):
        return maplen / ref_lens[ref] * 100
    cov_ref_lens["% Reference Covered"] = cov_ref_lens.apply(
        lambda x: perc_len(x["maplen"], x["Reference_Name"]), axis=1
    )
    cov_ref_lens["% Reference Covered"] = (
        cov_ref_lens["% Reference Covered"].map(lambda x: f"{x:.2f}").astype(float)
    )
    cov_ref_lens = cov_ref_lens[
        ["Sample", "Reference_Name", "% Reference Covered"]
    ].rename(columns={"Reference_Name": "Reference"})
    coverage_df = (
        coverage_df.groupby(["Sample", "Reference_Name"])
        .agg({"Coverage Depth": "mean"})
        .reset_index()
        .rename(
            columns={"Coverage Depth": "Mean Coverage", "Reference_Name": "Reference"}
        )
    )
    coverage_df["Mean Coverage"] = (
        coverage_df[["Mean Coverage"]].applymap(lambda x: f"{x:.0f}").astype(float)
    )
    summary_df = (
        reads_df.merge(cov_ref_lens, "left")
        .merge(coverage_df, "left")
        .merge(alleles_df, "left")
        .merge(indels_df, "left")
        .merge(allsamples_df, "outer", on="Sample")
    )
    summary_df['Reference'] = summary_df['Reference'].fillna('')
    summary_df = summary_df.fillna(0)
    return summary_df


def generate_dfs(irma_path):
    print("Building coverage_df")
    coverage_df = irma2pandas.dash_irma_coverage_df(irma_path)
    with open(f"{irma_path}/coverage.json", "w") as out:
        coverage_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> coverage_df saved to {out.name}")
    print("Building read_df")
    read_df = irma2pandas.dash_irma_reads_df(irma_path)
    with open(f"{irma_path}/reads.json", "w") as out:
        read_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> read_df saved to {out.name}")
    print("Build vtype_df")
    vtype_df = irma2pandas.dash_irma_sample_type(read_df)
    # Get most common vtype/sample
    with open(f"{irma_path}/vtype.json", "w") as out:
        vtype_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> vtype_df saved to {out.name}")
    print("Building alleles_df")
    alleles_df = irma2pandas.dash_irma_alleles_df(irma_path)
    with open(f"{irma_path}/alleles.json", "w") as out:
        alleles_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> alleles_df saved to {out.name}")
    print("Building indels_df")
    indels_df = irma2pandas.dash_irma_indels_df(irma_path)
    with open(f"{irma_path}/indels.json", "w") as out:
        indels_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> indels_df saved to {out.name}")
    print("Building ref_data")
    ref_lens = irma2pandas.reference_lens(irma_path)
    segments, segset, segcolor = irma2pandas.returnSegData(coverage_df)
    with open(f"{irma_path}/ref_data.json", "w") as out:
        json.dump(
            {
                "ref_lens": ref_lens,
                "segments": segments,
                "segset": segset,
                "segcolor": segcolor,
            },
            out,
        )
        print(f"  -> ref_data saved to {out.name}")
    print("Building dais_vars_df")
    dais_vars_df = dais2pandas.compute_dais_variants(f"{irma_path}/dais_results")
    with open(f"{irma_path}/dais_vars.json", "w") as out:
        dais_vars_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> dais_vars_df saved to {out.name}")
    print("Building irma_summary_df")
    irma_summary_df = irma_summary(
        irma_path, samplesheet, read_df, indels_df, alleles_df, coverage_df, ref_lens
    )
    print("Building nt_sequence_df")
    nt_seqs_df = irma2pandas.dash_irma_sequence_df(irma_path)
    def flu_dais_modifier(vtype_df, dais_seq_df):
        tmp = vtype_df.groupby(['Sample','vtype']).count().reset_index().groupby(['Sample'])['vtype'].max().reset_index()
        vtype_dic = dict(zip(tmp.Sample, tmp.vtype))
        dais_seq_df['Target_ref'] = dais_seq_df["Sample"].apply(lambda x: irma2pandas.flu_segs[vtype_dic[x[:-2]]][x[-1]])
        dais_seq_df["Sample"] = dais_seq_df["Sample"].str[:-2]
        dais_seq_df['Reference'] = dais_seq_df.apply(lambda x: which_ref(x["Sample"], x["Target_ref"], ref_proteins, irma_summary_df), axis=1)
        return dais_seq_df
    if virus == "flu":
        nt_seqs_df = flu_dais_modifier(vtype_df, nt_seqs_df)
    else:
        nt_seqs_df = nt_seqs_df.merge(irma_summary_df[['Sample', 'Reference']], how='left', on=['Sample'])
    print("Building pass_fail_df")
    pass_fail_df = pass_fail_qc_df(irma_summary_df, dais_vars_df, nt_seqs_df)
    with open(f"{irma_path}/pass_fail_qc.json", "w") as out:
        pass_fail_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> pass_fail_qc_df saved to {out.name}")
    pass_fail_seqs_df = pass_fail_df.reset_index().melt(id_vars='Sample').merge(nt_seqs_df, how='left', on=['Sample','Reference']).rename(columns={'value':'Reasons'})
    # Print nt sequence fastas
    pass_fail_seqs_df.loc[(pass_fail_seqs_df['Reasons'] == 'Pass') | (pass_fail_seqs_df['Reasons'] == "Premature stop codon")].apply(lambda x: seq_df2fastas(irma_path, x['Sample'], x['Reference'], x['Sequence'], 'nt', output_name='amended_consensus.fasta'), axis=1)
    aa_seqs_df = dais2pandas.seq_df(f"{irma_path}/dais_results")
    if virus == 'flu':
        aa_seqs_df = flu_dais_modifier(vtype_df, aa_seqs_df)
    aa_seqs_df['Reference'] = aa_seqs_df.apply(lambda x: which_ref(x["Sample"], x["Protein"], ref_proteins, irma_summary_df), axis=1)
    pass_fail_aa_df = pass_fail_df.reset_index().melt(id_vars='Sample').merge(aa_seqs_df, how='left', on=['Sample','Reference']).rename(columns={'value':'Reasons'})
    # Print aa sequence fastas
    pass_fail_aa_df.loc[(pass_fail_aa_df['Reasons'] == 'Pass') | (pass_fail_aa_df['Reasons'] == "Premature stop codon")].apply(lambda x: seq_df2fastas(irma_path, x['Sample'], x['Protein'], x['AA Sequence'], 'nt', output_name='amino_acid_consensus.fasta'), axis=1)
    with open(f"{irma_path}/nt_sequences.json", "w") as out:
        nt_seqs_df.to_json(out, orient="split")
        print(f"  -> nt_sequence_df saved to {out.name}")
    irma_summary_df = irma_summary_df.merge(pass_fail_df.reset_index().melt(id_vars=["Sample"], value_name="Reasons"), how='left', on=['Sample','Reference'])
    def noref(ref):
        if str(ref) == '':
            return 'N/A'
        else:
            return ref
    irma_summary_df['Reference'] = irma_summary_df['Reference'].apply(lambda x: noref(x))
    irma_summary_df['Reasons'] = irma_summary_df['Reasons'].fillna('Fail')
    irma_summary_df = irma_summary_df.rename(columns={'Reasons': 'Pass/Fail Reason'})
    with open(f"{irma_path}/irma_summary.json", "w") as out:
        irma_summary_df.to_json(out, orient="split", double_precision=3)
        print(f"  -> irma_summary_df saved to {out.name}")
    return read_df, coverage_df, segments, segcolor, pass_fail_df

def seq_df2fastas(irma_path, sample, reference, sequence, nt_or_aa, output_name=False):
    if not output_name:
        output_name = f"{nt_or_aa}_{sample}_{reference}.fasta"
    with open(f"{irma_path}/{output_name}", 'a+') as out:
        print(f">{sample}|{reference}\n{sequence}", file=out)

###################################################################
# Figures
###################################################################

def pivot4heatmap(coverage_df):
    if "Coverage_Depth" in coverage_df.columns:
        cov_header = "Coverage_Depth"
    else:
        cov_header = "Coverage Depth"
    df2 = coverage_df[["Sample", "Reference_Name", cov_header]]
    df3 = df2.groupby(["Sample", "Reference_Name"]).mean().reset_index()
    try:
        df3[["Subtype", "Segment", "Group"]] = df3["Reference_Name"].str.split(
            "_", expand=True
        )
    except ValueError:
        df3["Segment"] = df3["Reference_Name"]
    df4 = df3[["Sample", "Segment", cov_header]]
    return df4


def createheatmap(irma_path, coverage_means_df):
    print(f"Building coverage heatmap")
    if "Coverage_Depth" in coverage_means_df.columns:
        cov_header = "Coverage_Depth"
    else:
        cov_header = "Coverage Depth"
    coverage_means_df = coverage_means_df.pivot(index='Sample',columns='Segment').fillna(0).reset_index().melt(id_vars='Sample', value_name=cov_header).drop([None], axis=1)
    cov_max = coverage_means_df[cov_header].max()
    if cov_max <= 200:
        cov_max = 200
    elif cov_max >= 1000:
        cov_max = 1000
    fig = go.Figure(
        data=go.Heatmap(  # px.imshow(df5
            x=list(coverage_means_df["Sample"]),
            y=list(coverage_means_df["Segment"]),
            z=list(coverage_means_df[cov_header]),
            zmin=0,
            zmid=100,
            zmax=cov_max,
            colorscale="gnbu",
            hovertemplate="%{y} = %{z:,.0f}x<extra>%{x}<br></extra>"
        )
    )
    fig.update_layout(legend=dict(x=0.4, y=1.2, orientation="h"))
    fig.update_xaxes(side="top")
    pio.write_json(fig, f"{irma_path}/heatmap.json")
    print(f"  -> coverage heatmap json saved to {irma_path}/heatmap.json")


def create_passfail_heatmap(irma_path, pass_fail_df):
    print("Building pass_fail_heatmap")
    pass_fail_df = pass_fail_df.fillna('No assembly').reset_index().melt(id_vars=["Sample"], value_name="Reasons")
    if virus == 'flu':
        pass_fail_df['Reference'] = pass_fail_df['Reference'].apply(lambda x: x.split('_')[1])
    pass_fail_df = pass_fail_df.dropna()
    def assign_number(reason):
        if reason == 'No assembly':
            return 4
        elif reason == 'Pass':
            return -4#numpy.nan
        elif reason == 'Premature stop codon':
            return -1
        else:
            return len(reason.split(';'))
    pass_fail_df['Number'] = pass_fail_df['Reasons'].apply(lambda x: assign_number(x))
    pass_fail_df['Reasons'].fillna('No assembly')
    fig = go.Figure(data=go.Heatmap(
        x=list(pass_fail_df["Sample"]),
        y=list(pass_fail_df["Reference"]),
        z=list(pass_fail_df["Number"]),
        customdata=list(pass_fail_df['Reasons']),
        zmin=-4,
        zmax=6,
        zmid=1,
        colorscale='blackbody_r',# 'ylorrd',
        hovertemplate="%{x}<br>%{customdata}<extra>%{y}<br></extra>"
    ))
    fig.update_xaxes(side="top")
    fig.update_traces(showscale=False)
    fig.update_layout(paper_bgcolor='white', plot_bgcolor='white')
    pio.write_json(fig, f"{irma_path}/pass_fail_heatmap.json")
    print(f"  -> pass_fail heatmap json saved to {irma_path}/pass_fail_heatmap.json")


def createsankey(irma_path, read_df):
    print(f"Building read sankey plot")
    for sample in read_df["Sample"].unique():
        sankeyfig = irma2pandas.dash_reads_to_sankey(
            read_df[read_df["Sample"] == sample]
        )
        pio.write_json(sankeyfig, f"{irma_path}/readsfig_{sample}.json")
        print(f"  -> read sankey plot json saved to {irma_path}/readsfig_{sample}.json")


def createReadPieFigure(irma_path, read_df):
    print(f"Building barcode distribution pie figure")
    read_df = read_df[read_df["Record"] == "1-initial"]
    fig = px.pie(read_df, values="Reads", names="Sample")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.write_json(f"{irma_path}/barcode_distribution.json")
    print(
        f"  -> barcode distribution pie figure saved to {irma_path}/barcode_distribution.json"
    )


def createSampleCoverageFig(sample, df, segments, segcolor, cov_linear_y):
    if "Coverage_Depth" in df.columns:
        cov_header = "Coverage_Depth"
    else:
        cov_header = "Coverage Depth"
    if "HMM_Position" in df.columns:
        pos_header = "HMM_Position"
    else:
        pos_header = "Position"
    def zerolift(x):
        if x == 0:
            return 0.000000000001
        return x
    if not cov_linear_y:
        df[cov_header] = df[cov_header].apply(lambda x: zerolift(x))
    df2 = df[df["Sample"] == sample]
    fig = go.Figure()
    if "SARS-CoV-2" in segments:
        # y positions for gene boxes
        oy = (
            max(df2[cov_header]) / 10
        )  # This value determines where the top of the ORF box is drawn against the y-axis
        if not cov_linear_y:
            ya = 0.9
        else:
            ya = 0 - (max(df2[cov_header]) / 20)
        orf_pos = {
            "orf1ab": (266, 21556),
            "S": [21563, 25385],
            "orf3a": [25393, 26221],
            "E": [26245, 26473],
            "M": [26523, 27192],
            "orf6": [27202, 27388],
            "orf7ab": [27394, 27888],
            "orf8": [27894, 28260],
            "N": [28274, 29534],
            "orf10": [29558, 29675],
        }
        color_index = 0
        for orf, pos in orf_pos.items():
            fig.add_trace(
                go.Scatter(
                    x=[pos[0], pos[1], pos[1], pos[0], pos[0]],
                    y=[oy, oy, 0, 0, oy],
                    fill="toself",
                    fillcolor=px.colors.qualitative.T10[color_index],
                    line=dict(color=px.colors.qualitative.T10[color_index]),
                    mode="lines",
                    name=orf,
                    opacity=0.4,
                )
            )
            color_index += 1
    for g in segments:
        if g in df2["Reference_Name"].unique():
            try:
                g_base = g.split("_")[1]
            except IndexError:
                g_base = g
            df3 = df2[df2["Reference_Name"] == g]
            fig.add_trace(
                go.Scatter(
                    x=df3[pos_header],
                    y=df3[cov_header],
                    mode="lines",
                    line=go.scatter.Line(color=segcolor[g_base]),
                    name=g,
                    customdata=tuple(["all"] * len(df3["Sample"])),
                )
            )
    fig.add_shape(
        type="line",
        x0=0,
        x1=df2[pos_header].max(),
        y0=qc_values[platform]['mean_cov'],
        y1=qc_values[platform]['mean_cov'],
        line=dict(color="Black", dash="dash", width=5),
    )
    ymax = df2[cov_header].max()
    if not cov_linear_y:
        ya_type = "log"
        ymax = ymax ** (1 / 10)
    else:
        ya_type = "linear"
    fig.update_layout(
        height=600,
        title=sample,
        yaxis_title="Coverage",
        xaxis_title="Reference Position",
        yaxis_type=ya_type,
        yaxis_range=[0, ymax],
    )
    return fig


def createcoverageplot(irma_path, coverage_df, segments, segcolor):
    samples = coverage_df["Sample"].unique()
    print(f"Building coverage plots for {len(samples)} samples")
    for sample in samples:
        coveragefig = createSampleCoverageFig(
            sample, coverage_df, segments, segcolor, False
        )
        pio.write_json(coveragefig, f"{irma_path}/coveragefig_{sample}_linear.json")
        print(f"  -> saved {irma_path}/coveragefig_{sample}_linear.json")
        coveragefig = createSampleCoverageFig(
            sample, coverage_df, segments, segcolor, True
        )
        pio.write_json(coveragefig, f"{irma_path}/coveragefig_{sample}_log.json")
        print(f"  -> saved {irma_path}/coveragefig_{sample}_log.json")
    print(f" --> All coverage jsons saved")


def generate_figs(irma_path, read_df, coverage_df, segments, segcolor, pass_fail_df):
    createReadPieFigure(irma_path, read_df)
    createsankey(irma_path, read_df)
    createheatmap(irma_path, pivot4heatmap(coverage_df))
    create_passfail_heatmap(irma_path, pass_fail_df)
    createcoverageplot(irma_path, coverage_df, segments, segcolor)


if __name__ == "__main__":
    generate_figs(irma_path, *generate_dfs(irma_path))
