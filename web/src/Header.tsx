import { useNavigate, useLocation } from "react-router-dom";
import "./Header.css"
function Header(){
    const navigate = useNavigate();
    const location = useLocation();

    return <div id="header">
        <div className="btn btn-header" onClick={()=>navigate("/" + location.search)}>{"Home"}</div> 
        <div className="btn btn-header" onClick={()=>navigate("/insert" + location.search)}>{"Insert"}</div> 
        <div className="btn btn-header" onClick={()=>navigate("/show" + location.search)}>{"Show"}</div> 
    </div>
}

export default Header;