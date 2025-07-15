import { useEffect, useRef, useState } from 'react'
import './Home.css'
import Header from './Header';
import { useNavigate } from 'react-router-dom';
import auth from './Auth';


interface line {
  id: number,
  link:string,
  type: number,
  processedType: string,
  expect: number,
  result: string,
  response: string
  ipv6: string | undefined
}

function Home() {
    const navigate = useNavigate();

    const [ lines, setLines ] = useState<line[]>([]);
    const [ executeValue, setExecuteValue ] = useState("");
    const [ isValidExecuteValue, setIsValidExecuteValue ] = useState(true);
    const [ result, setResult ] = useState({ recall: 0, precision: 0, specificity: 0, accuracy: 0 });
    const [ response, _ ] = useState([false,""]);
    const [ page, setPage ] = useState(0);
    const [ postsPerPage, setPostsPerPage ] = useState(10);
    const [ nPosts, setNPosts ] = useState(0);
    
    const n_pages = useRef(0);

    const refs = {
        inputPostsPerPage: useRef<HTMLInputElement>(null)
    }

    const [ isAdmin, setIsAdmin ] = useState(false);

    const transformData = (data: any) => {
        const types = [
            "Outro",
            "Saúde e Ciência",
            "Geopolítica",
            "História",
            "Esporte e Cultura",
            "Atualidades"
        ];
        return data.map((line: any)=>{ return {...line, processedType: types[Number(line.type)], result: line.result == 2 ? "-" : String(line.result) } });
    };
    
    const onExecuteInput = (e: any) => {
            setExecuteValue(previousValue=>{
                const value: string = e.target.value;
                if (value == "" || /^\d+$/.test(value) || /^\d+-$/.test(value) || /^\d+-\d+$/.test(value)){
                    if (/^\d+-\d+$/.test(value)){
                        const parts = value.split("-");
                        const id_start = Number(parts[0]);
                        const id_end = Number(parts[1]);
                        
                        setIsValidExecuteValue(id_end >= id_start && id_end <= lines[lines.length-1].id);
                    } else {
                        setIsValidExecuteValue(false);
                    }
                    return value;
                }

                setIsValidExecuteValue(false);

                return previousValue;
            });
    }

    const executeVerify = () => {
        if (!isValidExecuteValue) return;

        const parts = executeValue.split("-");
        const id_start = parts[0];
        const id_end = parts[1];

        setIsValidExecuteValue(false);

        auth.post(auth.server + "/verify", {
            id_start,
            id_end,
            page,
            postsPerPage
        }).then(response=>{
            if (response.data.result == "true"){
                const data = response.data.data;
                setExecuteValue(`1-${data.length}`);
                setLines(transformData(data));
            }
            if (/^\d+-\d+$/.test(executeValue)){
                const parts = executeValue.split("-");
                const id_start = Number(parts[0]);
                const id_end = Number(parts[1]);
                setIsValidExecuteValue(id_end >= id_start && id_end <= lines[lines.length-1].id);
            } else {
                setIsValidExecuteValue(false);
            }
        });
    }

    const deleteLine = (id: number) => {
        auth.post(auth.server + "/delete", {
            id,
            page,
            postsPerPage
        }).then(response=>{
            if (response.data.result == "true"){
                const data = response.data.data;
                setExecuteValue(`1-${data.length}`);
                setLines(transformData(data));
            }
        });
    }
    
    const switchResponse = (_: line) => {
        
    }

    const closeResponse = () => {
    }

    useEffect(()=>{
        auth.post(auth.server + "/list", { page, postsPerPage }).then(response=>{
            if (response.data.isAdmin){
                setIsAdmin(true);
            }
            const data = response.data.data;
            n_pages.current = Math.floor(data[0].n_posts / postsPerPage);
            setNPosts(data[0].n_posts);
            setExecuteValue(`1-${data.length}`);
            setLines(transformData(data));
        });
    },[page,postsPerPage]);

    useEffect(()=>{
        const query = new URLSearchParams(location.search);
        if (query.has("page")){
            setPage(Number(query.get("page")!));
        } else {
            navigate("/?page=0");
        }
    },[location.search]);

    useEffect(()=>{
        const getValue = (value: number) => isNaN(value) ? 0 : value;

        const filteredLines = lines.filter(line=>Number(line.result) != 2 );
        const VP = filteredLines.filter(line=>line.expect == 1 && Number(line.result) == 1).length;
        const VN = filteredLines.filter(line=>line.expect == 0 && Number(line.result) == 0).length;
        const FP = filteredLines.filter(line=>line.expect == 0 && Number(line.result) == 1).length;
        const FN = filteredLines.filter(line=>line.expect == 1 && Number(line.result) == 0).length;

        const recall = getValue(VP / (VP + FN));
        const precision = getValue(VP / (VP + FP));
        const specificity = getValue(VN / (VN + FP));
        const accuracy = getValue((VP + VN) / (VP + VN + FP + FN));

        setResult({ recall, precision, specificity, accuracy });

    },[lines]);

    const editLine = (line: line) => {
        const query = new URLSearchParams(location.search);
        query.set("id", String(line.id));
        navigate("/edit?" + query.toString());
    }

    return <>
        <Header></Header>
        <div id="home" className='page'>
            <div id='table'>
                <div id='head'>
                    <div className="line-id">Id</div>
                    <div className="line-link">Link</div>
                    <div className="line-expect">Expectativa</div>
                    <div className="line-type">Tipo</div>
                    <div className="line-result">Resultado</div>
                    <div className='line-options'>Opções</div>
                    {isAdmin ? <div className='ipv6'>Ipv6</div> : <></> }
                </div>
                <div id="content">{lines.map((line, i: number)=>{
                    return <div className='line' key={String(i)}>
                        <div className="line-id">{line.id}</div>
                        <a className="line-link" href={line.link} onClick={(e)=>{e.preventDefault(); window.open(line.link, "blank")}}>
                            <div className='line-link-text'>{line.link}</div>
                        </a>
                        <div className="line-expect">{line.expect}</div>
                        <div className="line-type">{line.processedType}</div>
                        <div className="line-result">{line.result}</div>
                        <div className="line-options">
                            <div className='delete-option btn-option' onClick={()=>deleteLine(line.id)}>d</div>
                            <div className="edit-option btn-option" onClick={()=>editLine(line)}>e</div>
                            <div className="complete-option btn-option" onClick={()=>switchResponse(line)}>c</div>
                        </div>
                        { isAdmin ? <div className='line-ipv6'>{line.ipv6}</div> : <></> }
                    </div>
                })}</div>
            </div>
            <div className='switch-page-container'>
                <div id="btn-switch-pages">
                    <div className='btn-switch-page' onClick={()=>navigate("/?page=" + Math.max(page - 1, 0))}>{Math.max(page,0)}</div>
                    <div className='btn-switch-page' onClick={()=>navigate("/?page=" + Math.min(page + 1, n_pages.current))}>{page + 2}</div>
                </div>
                <div>{nPosts} posts</div>
                <div>Posts por página</div>
                <input defaultValue="10" ref={refs.inputPostsPerPage} type='number' id="input-posts-per-page"></input>
                <button onClick={()=>setPostsPerPage(Number(refs.inputPostsPerPage.current!.value))} id="posts-per-page">Atualizar</button>
            </div>
            <div id="execute-div">
                <div className='execute-group'>
                    <div className='label'>Links para executar:</div>
                    <input value={executeValue} onInput={onExecuteInput}></input>
                </div>
                <div style={isValidExecuteValue ? { opacity: "1", cursor: "pointer" } : { opacity: "0.5", cursor: "initial" }} id="execute-btn" className='btn' onClick={executeVerify}>Executar</div>
            </div>
            <div id="result">
                <div id="result1">Sensibilidade: {result.recall}</div>
                <div id="result2">Precisão: {result.precision}</div>
                <div id="result3">Especificidade: {result.specificity}</div>
                <div id="result4">Acurácia: {result.accuracy}</div>
            </div>
            <div id="response-menu-a" style={{ display: response[0] ? "block" : "none" }}></div>
            <div style={{ display: response[0] ? "block" : "none" }} id="response-menu">
                <div id="response-x" onClick={closeResponse}></div>
                <div id="response"></div>
            </div>
        </div>
    </>
}

export default Home;
