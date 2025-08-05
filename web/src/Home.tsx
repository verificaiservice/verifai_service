import React, { useEffect, useLayoutEffect, useRef, useState } from 'react'
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

// function Comp({line, i}:{line:line, i:number}) {
//     const [ remove, setRemove ]=useState(false)
//     useLayoutEffect(()=>{
//         return ()=>{
//             setRemove(true);
//         }
//     }, [])

//     return remove ? <></> : 
// }

function Home() {
    const navigate = useNavigate();

    const [ lines, setLines ] = useState<line[]>([]);
    const [ executeValue, setExecuteValue ] = useState("");
    const [ isValidExecuteValue, setIsValidExecuteValue ] = useState(true);
    const [ result, setResult ] = useState({ recall: 0, precision: 0, specificity: 0, accuracy: 0 });
    const [ response, _ ] = useState([false,""]);
    const [ page, setPage ] = useState(-1);
    const [ postsPerPage, setPostsPerPage ] = useState(10);
    const [ nPosts, setNPosts ] = useState(0);
    
    const n_pages = useRef(0);

    const refs = {
        inputPostsPerPage: useRef<HTMLInputElement>(null),
        link: useRef<HTMLInputElement>(null),
        type: useRef<HTMLSelectElement>(null),
        expect: useRef<HTMLSelectElement>(null)
    }

    const [ isAdmin, setIsAdmin ] = useState(false);

    const [ editLine, setEditLine ] = useState<line | null>(null);

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
        if (page >= 0){
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
        }
    },[page,postsPerPage]);

    const process = () => {
        console.log(window.instgrm)
        window.instgrm && window.instgrm.Embeds.process();
    }
    useEffect(()=>{
            process()

        // const timeout = setTimeout(() => {
        //     process()
        // }, 1000); // pequeno delay para garantir que os blockquotes estão no DOM

        // return () => clearTimeout(timeout);
    },[result])

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

    // const editLine = (line: line) => {
    //     const query = new URLSearchParams(location.search);
    //     query.set("id", String(line.id));
    //     navigate("/edit?" + query.toString());
    // }

    const verifyInsert = ()=>{
        if (editLine){
            setEditLine(null);

            var link = editLine.link.split("?")[0];
            link = link.endsWith("/") ? link.slice(0, -1) : link;
            const type = refs.type.current!.value;
            const expect = refs.expect.current!.value;

            if (!(link.startsWith("https://www.instagram.com/p/") || link.startsWith("https://www.instagram.com/reel/") || link.startsWith("https://www.instagram.com/share/p/") || link.startsWith("https://wwww.instagram.com/share/reel/"))) return;
            
            const id = editLine.id;
            auth.post(auth.server + "/edit", { 
               id, type, expect 
            }).then(response=>{
                const query = new URLSearchParams(location.search);
                query.delete("id");
                response.data.result=="true" && navigate("/?"+query.toString());
            })
        } else {
            var link = refs.link.current!.value.split("?")[0];
            link = link.endsWith("/") ? link.slice(0, -1) : link;
            const type = refs.type.current!.value;
            const expect = refs.expect.current!.value;

            if (!(link.startsWith("https://www.instagram.com/p/") || link.startsWith("https://www.instagram.com/reel/") || link.startsWith("https://www.instagram.com/share/p/") || link.startsWith("https://wwww.instagram.com/share/reel/"))) return;
            
            auth.post(auth.server + "/insert", { 
                link, type, expect 
            }).then(response=>{
                if (response.data.result == "false" && response.data.message && response.data.message == "exists"){
                    setTimeout(()=>{
                        navigate("/"+location.search);
                    },1500);
                }
                response.data.result=="true" && navigate("/"+location.search);
            })
        }
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
                            <div className="edit-option btn-option" onClick={()=>setEditLine(line)}>e</div>
                            <div className="complete-option btn-option" onClick={()=>switchResponse(line)}>c</div>
                        </div>
                        { isAdmin ? <div className='line-ipv6'>{line.ipv6}</div> : <></> }
                    </div>
                })}</div>
            </div>
            <div style={{overflow:"hidden", overflowY: "auto", height: "700px"}} id='posts'>{lines.sort((a,b)=>b.id - a.id).map((line, i: number)=>{
                return <div className={'post post-'+String(i)} key={String(i * 1000 + line.id)}>
                    <blockquote className="instagram-media" data-instgrm-permalink={line.link} data-instgrm-version="14"></blockquote>
                    <div className='post-options'>
                        {line.expect == 3 ? <i className="fa-duotone fa-solid fa-square-check" style={{"--fa-primary-color": "#ffffff", "--fa-secondary-color": "#00ff11", "--fa-secondary-opacity": 1} as React.CSSProperties}></i> : <i className="fa-solid fa-xmark" style={{color: "#ff0000"}}></i>}
                        <div className='delete-option btn-option' onClick={()=>deleteLine(line.id)}>d</div>
                        <div className="edit-option btn-option" onClick={()=>setEditLine(line)}>e</div>
                        <div className="complete-option btn-option" onClick={()=>switchResponse(line)}>c</div>
                    </div>
                </div>
            })}</div>
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
            <div id="edit-menu" style={{display: editLine ? "flex" : "none" }}>
                <div id="form">
                    <div id="x-edit-menu" onClick={()=>setEditLine(null)}>X</div>
                    <div className='group'>
                        <div className='label'>Link:</div>
                        <input defaultValue={editLine ? editLine.link : ""} readOnly={!!editLine}  ref={refs.link} id="link" className='group-input'></input>
                    </div>
                    <div className='group'>
                        <div className='label'>Tipo de conteúdo:</div>
                        <select className='insert-select group-input' defaultValue={editLine ? editLine.type : 1} ref={refs.type} id="type">
                            <option value="1">Saúde e Ciência</option>
                            <option value="2">Geopolítica</option>
                            <option value="3">História</option>
                            <option value="4">Esporte e Cultura</option>
                            <option value="5">Atualidades</option>
                            <option value="0">Outro</option>
                        </select>
                    </div>
                    <div className='group'>
                        <div className='label'>Veracidade:</div>
                        <select className='insert-select group-input' defaultValue={editLine ? editLine.expect : 1} ref={refs.expect} id="expect">
                            <option value="1">Verdadeiro</option>
                            <option value="0">Falso</option>
                        </select>
                    </div>
                    <div id="send" className='btn' onClick={verifyInsert}>Inserir</div>
                </div>
            </div>
        </div>
    </>
}

export default Home;
