import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from "react-router-dom";
import "./Insert.css";
import Header from './Header';
import auth from './Auth';


interface line {
  id: number,
  link:string,
  type: number,
  processedType: string,
  expect: number,
  result: string,
  response: string
}

function Insert(){
    const navigate = useNavigate();
    const location = useLocation();

    const refs = {
        link: useRef<HTMLInputElement>(null),
        type: useRef<HTMLSelectElement>(null),
        expect: useRef<HTMLSelectElement>(null)
    }
    const [ editLine, setEditLine ] = useState<line | null>(null);
    const [ exists, setExists ]= useState(false);

    const verifyInsert = ()=>{
        if (editLine){
            var link = editLine.link.split("?")[0];
            link = link.endsWith("/") ? link.slice(0, -1) : link;
            const type = refs.type.current!.value;
            const expect = refs.expect.current!.value;

            if (!(link.startsWith("https://www.instagram.com/p/") || link.startsWith("https://www.instagram.com/reel/") || link.startsWith("https://www.instagram.com/share/p/") || link.startsWith("https://wwww.instagram.com/share/reel/"))) return;
            
            const id = new URLSearchParams(location.search).get("id");
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
                    setExists(true);
                    setTimeout(()=>{
                        navigate("/"+location.search);
                    },1500);
                }
                response.data.result=="true" && navigate("/"+location.search);
            })
        }
    }

    useEffect(()=>{
        if (location.pathname == "/edit"){
            const id = new URLSearchParams(location.search).get("id");
            auth.post(auth.server + "/edit", { 
                type: "get",
                id
            }).then(response=>{
                refs.type.current!.value = response.data.data.type;
                refs.expect.current!.value = response.data.data.expect;
                setEditLine(response.data.data);
            });
        }
    },[]);

    return <>
        <Header></Header>
        <div id="insert" className='page'>
            <div id="form">
                {exists ? <div>Já existe</div> : <></>}
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
    </>
}

export default Insert