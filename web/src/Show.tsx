import { useEffect, useState } from "react";
import Header from "./Header";
import auth from "./Auth";

function Show(){
    const [ ip, setIp ] = useState("");

    useEffect(()=>{
        auth.get(auth.server + "/ip").then(response=>{
            setIp(response.data);
        })
    },[]);
    return <>
        <Header></Header>
        <div style={{  marginTop: "50px" }}>{btoa(ip)}</div>
    </>
}

export default Show;