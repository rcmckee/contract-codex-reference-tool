import docx
import pysos
import hashlib
import re 
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import semantic_search
from difflib import SequenceMatcher

# process input to make database

def get_parts_of_maingroup(part):
    label, value = part.split(':')
    match label:
        case "Main group notes":
            return ('maingroup_notes', value)
        case "Sub group":
            return ('sub_group', value)
        case "Sub group notes":
            return ('sub_group_note', value)
        case "Sub group clause":
            return ('sub_group_clause', value)
        case _:
            print("fallback case of get_parts_of_main_group")
            return ('fallback','')


def process_text_to_dict_of_groups(all_text):
    
    parts = all_text.split('Main group:')

    groups = {}
    
    for i in parts:
        main_group = None
        sub_groups = {} 
        if len(i.strip()) > 0:
            sub_group = None
            for indx, p in enumerate(i.split('\n')):
                
                if indx == 0:
                     main_group = p.strip()
                     print(f'main group = {main_group}')
                     groups[main_group] = {}
                elif len(p) > 0:
                    k,v = get_parts_of_maingroup(p)
                    match k:
                        case 'maingroup_notes':
                            groups[main_group]['maingroup_notes'] = v.strip()
                        case 'sub_group':
                            sub_group = v.strip()
                            sub_groups[sub_group] = {'sub_group_note': '', 'sub_group_clauses': []}
                        case 'sub_group_note':
                            sub_groups[sub_group]['sub_group_note'] = v.strip()
                        case 'sub_group_clause':
                            sub_groups[sub_group]['sub_group_clauses'].append(v.strip())
        if main_group != None:
            groups[main_group]['sub_groups'] = sub_groups
        print(groups)
    return groups
    
    

def hash_text(text):
    hash_object = hashlib.md5(text.encode())
    return hash_object.hexdigest()



def is_clause_sub_clause(clauses_to_search):
    for i,(k,v) in enumerate(clauses_to_search):
    
        if 'larger_clause' in v:
            v['larger_clause'] = hash_text(v['larger_clause'])
        v |= {'clause':k}
    
    
        new_db[hash_text(k)] = v
    


def make_sentences_from_paragraph(text): 
    data = []
    sents = re.split(r"[;.]\s*", text)
    for s in sents:
        data.append(s)
    return data
    

def build_custom_db_from_text(all_text):
    """
    use this function to convert text of a custom clause codex. The result is a dictionary that can be added to the contract codex database for similarity search.
    The output dictionary will follow this pattern: {'main_group': {'maingroup_notes':'','sub_groups':{'sub_group_1_name':{'sub_group_note':'','sub_group_clauses':['a','b']}}}}

    The input text should be formated as follows:
        all_text = '''
                    Main group: first k
                    
                    Main group notes: this is v and everything below
                    
                    Sub group: a
                    Sub group notes: a1xxxxxx
                    Sub group clause: a1axxxxxx
                    Sub group clause: a1bxxxxxx
                    
                    Sub group: b
                    Sub group notes: b1xxxxxx
                    Sub group clause: b1axxxxxx
                    Sub group clause: b1bxxxxxx
                    
                    Main group: second k
                    
                    Main group notes: this is v and everything below
                    
                    Sub group: 2a
                    Sub group notes: 2a1xxxxxx
                    Sub group clause: 2a1axxxxxx
                    Sub group clause: 2a1bxxxxxx
                    
                    Sub group: 2b
                    Sub group notes: 2b1xxxxxx
                    Sub group clause: 2b1axxxxxx
                    Sub group clause: 2b1bxxxxxx
                    '''

    """

    all_groups = process_text_to_dict_of_groups(all_text)

    hash_db_personal = pysos.Dict('pysos_hash_values_personal')
        
    data_db_personal = pysos.Dict('pysos_meta_data_db_personal')

    clauses_to_search = {}
    for k,v in all_groups.items():
        for a,b in v['sub_groups'].items():
                
            for c in b['sub_group_clauses']:
                clauses_to_search[c] = {'maingroup':k,'subgroup':a}
                for s in make_sentences_from_paragraph(c):
                    if len(s)>0:
                        clauses_to_search[s] = {'maingroup':k,'subgroup':a, 'larger_clause':c}
        
            
    data_db_personal = clauses_to_search
        
    for i,(k,v) in enumerate(clauses_to_search.items()):
            
        if 'larger_clause' in v:
            v['larger_clause'] = hash_text(v['larger_clause'])
        v |= {'clause':k}
            
            
        hash_db_personal[hash_text(k)] = v

    hash_db |= hash_db_personal
    data_db |= data_db_personal



def getText(filename):
    doc = docx.Document(filename)
    fullText = []
    for para in doc.paragraphs:
        print()
        try:
            if len(para.text.strip()) > 0:
                fullText.append(para.text)
        except:
            pass
    return fullText





def show_redlines(a, b):
    #in pure python instead of redlines package which doesn't work on snowflake
    a_words = a.split()
    b_words = b.split()

    matcher = SequenceMatcher(None, a_words, b_words)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.extend(a_words[i1:i2])
        elif tag == "replace":
            result.extend([f"{w}" for w in a_words[i1:i2]])
            result.extend([f"{w}" for w in b_words[j1:j2]])
        elif tag == "delete":
            result.extend([f"{w}" for w in a_words[i1:i2]])
        elif tag == "insert":
            result.extend([f"{w}" for w in b_words[j1:j2]])

    return ' '.join(result)


def output_results_as_html_string(sentence_being_reviewed, matches):
    sentence_being_reviewed = sentence_being_reviewed.strip()
    match_outline_list = [f'{show_redlines(sentence_being_reviewed,match)}' for match in matches]
    match_outline_string = ''.join(match_outline_list)
    #codex_outline = db[db['clauses_to_search'][matches[0]]['maingroup']]['maingroup_subgroups_url'][0]
    codex_outline = db_meta_data[db_hash_values[hash_text(matches[0])]['maingroup']]['maingroup_subgroups_url'][0]
    main_clause_type = codex_outline[0]
    codex_outline = [f'{item}' for item in codex_outline[1:]]
    codex_outline = ''.join(codex_outline)
    #codex_url = db[db['clauses_to_search'][matches[0]]['maingroup']]['maingroup_subgroups_url'][1]
    codex_url = db_meta_data[db_hash_values[hash_text(matches[0])]['maingroup']]['maingroup_subgroups_url'][1]
    try:
        #larger_clause =  f" It may be part of a larger clause:{show_redlines(sentence_being_reviewed, db['clauses_to_search'][matches[0]]['larger_clause'])}"
        larger_clause =  f" It may be part of a larger clause:{show_redlines(sentence_being_reviewed, db_hash_values[db_hash_values[hash_text(matches[0])]['larger_clause']]['clause'])}"
    except:
      larger_clause = ""
    return f'''{sentence_being_reviewed}
    
    
        Expand Notes
            {editor}
            {button}
    

  See Analysis
        The most similar clauses are presented below with track changes to see the difference between your contract clause and the similar clauses.
        
            {match_outline_string}
        
        EXPLANATION OF THE LANGUAGE
        This clause resembles a {db_hash_values[hash_text(matches[0])]['maingroup']} and is likely part of a subgroup of the clause labeled {db_hash_values[hash_text(matches[0])]['subgroup']}:{larger_clause}

        Main Group: {db_hash_values[hash_text(matches[0])]['maingroup']}
        Main Group Notes: {db_meta_data[db_hash_values[hash_text(matches[0])]['maingroup']]['maingroup_notes']}

        Sub Group: {db_hash_values[hash_text(matches[0])]['subgroup']}
        Sub Group Notes: {db_meta_data[db_hash_values[hash_text(matches[0])]['maingroup']]['sub_groups'][db_hash_values[hash_text(matches[0])]['subgroup']]['sub_group_note']}

        For more information on this type of clause, see the page from Contract Codex


'''

def output_notmatch_as_html_string (sentence_being_reviewed, matches):
    return f'''{sentence_being_reviewed}
    
        
            Expand Notes
                {editor}
                {button}
        
        
            No sufficiently similar clauses were found in the database.
            Please review manually.
        
    
    '''




style = """body { font-family: sans-serif; }
        #editor {
            border: 1px solid #ccc;
            padding: 10px;
            min-height: 20px;
            margin-bottom: 10px;
        }
        button {
            padding: 8px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            cursor: pointer;
        }
        del { color: red; text-decoration: line-through; }
        ins { color: green; font-weight: bold; }
        .noteBoxes { border: 1px solid; border-radius: 5px; padding: 10px; margin: 10px 0; width: 90%; } .type1 { border-color: #E76F51; background-color: rgba(231, 111, 81, 0.1); } .type2 { border-color: #2A9D8F; background-color: rgba(42, 157, 143, 0.1); } .type3 { border-color: #0096C7; background-color: rgba(0, 150, 199, 0.1); } .type4 { border-color: #00B353; background-color: rgba(0, 179, 83, 0.1); } .picture { width: 15px; padding-right: 10px; }
        """

script = """
    function saveCurrentPage() {
        // Get the entire HTML content of the document
        const htmlContent = document.documentElement.outerHTML;

        // Create a Blob object from the HTML content
        const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });

        // Create a URL for the Blob
        const url = URL.createObjectURL(blob);

        // Create a temporary anchor element
        const a = document.createElement('a');
        a.href = url;
        a.download = 'saved_page.html'; // Suggested filename for the download
        a.style.display = 'none'; // Hide the anchor element

        // Append the anchor to the body, click it, and then remove it
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Revoke the object URL to free up resources
        URL.revokeObjectURL(url);
    }
"""

editor = """
        Add your notes here...
    """
button = """"""


def process_contract(input_file,cutoff_value,secondary_cutoff_value,db_hash_values,db_meta_data,clause_phrases,model,sentence_embeddings):
    doc_text = getText(input_file)



    html_string_result = ""


    for para in doc_text:
        # this should be matching paragraph
        if len(para.strip())==0:
            continue

        # Convert query sentence to embedding
        query_embedding = model.encode(para)
        
        ## Find top 3 most similar sentences
        hits = semantic_search(query_embedding, sentence_embeddings, top_k=3)
        matches = []

        if hits[0][0]['score'] > cutoff_value:

            for idx, hit in enumerate(hits[0]):

                if hit['score'] >= cutoff_value:
            
                    matches.append(f"{clause_phrases[hit['corpus_id']]}")

                
            if len(matches) > 0:
                html_string_result += output_results_as_html_string(para,matches)
        else:
            # if no matches found by paragraph then try breaking into sentences
            sentences = para.split('. ')

            for sentence in sentences:
                if len(sentence.strip())==0:
                    continue

                query_embedding = model.encode(sentence)
                hits = semantic_search(query_embedding, sentence_embeddings, top_k=3)
                matches = []

                if hits[0][0]['score'] > secondary_cutoff_value:

                    for idx, hit in enumerate(hits[0]):

                        if hit['score'] >= secondary_cutoff_value:
                    
                            matches.append(f"{clause_phrases[hit['corpus_id']]}")

                    
                    if len(matches) > 0: #to verify something was matched. otherwise enter no match
                        html_string_result += output_results_as_html_string(sentence,matches)
                else:
                    html_string_result += output_notmatch_as_html_string(sentence,matches)# output_notmatch_as_md(para,matches)
    
    html_output = f"""
    
        
        
        
        Contract Reference Tool
        
    
    
        Contract Reference Tool
        {button}
        
            
                {html_string_result}
            
        
        {button}
        
            Powered by the Contract Codex Community."""
    return html_output
