import { BrowserRouter as Router, Routes, Route } from 'react-router';
import Home from './Home';
import Insert from './Insert';
import './App.css';
import auth from './Auth';
import Show from './Show';

declare global {
    interface Window{
        instgrm: any
    }
}

function App() {

    auth.get(auth.server + "/has_defined").then(response=>{
    if (!response.data.setted){
        auth.get("https://verifaiservice.eneagonlosamigos.workers.dev/").then(response=>{
            const ipv6 = response.data;
            auth.post(auth.server + "/define", { ipv6 }).then(result=>{
                window.location.reload();
            });
        })
    }
});
    return (
        <Router>
            <Routes>
                <Route path="/" element={<Home/>} />
                <Route path="/edit" element={<Insert/>} />
                <Route path="/insert" element={<Insert/>} />
                <Route path="/show" element={<Show/>} />
            </Routes>
        </Router>
  )
}

export default App;