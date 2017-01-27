using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using WebSocketSharp;
using System.Linq;

public class DataTrack : MonoBehaviour {
	
	public WebSocket ws_cur;
    GameObject drone0;
    GameObject drone1;
    GameObject drone2;
    GameObject drone3;
    Rigidbody droneRigidbody;
    private Vector3 droneCoords;
    private Vector3 droneVelocity;
    private Vector3 goalCoords;

    private Vector3 dir0;
    private Vector3 dir1;
    private Vector3 dir2;
    private Vector3 dir3;

	private float timeSinceSend;

    public int success = 0;

    private InstantiateGoal instantiateGoal;

    public bool discrete;
    public float discreteMagnitude;

    private List<GameObject> drones;
	public Dictionary<int, CollisionDetect> colDets = new Dictionary<int, CollisionDetect>();
	public Dictionary<int, GameObject> goals = new Dictionary<int, GameObject>();
	private List<Movement> moves = new List<Movement> ();
    public bool netControlled = false;

    // Use this for initialization
    void Start () {
        drones = new List<GameObject>();
        timeSinceSend = Time.time;
        dir0 = new Vector3(1f, 0f, 0f); //right
        dir1 = new Vector3(0f, 0f, 1f); //up
        dir2 = new Vector3(0f, 0f, -1f); // down
        dir3 = new Vector3(-1f, 0f, 0f); //left
        instantiateGoal = gameObject.GetComponent<InstantiateGoal>();

        drones.Add(GameObject.Find("Drone0"));
        drones.Add(GameObject.Find("Drone1"));
        drones.Add(GameObject.Find("Drone2"));
        drones.Add(GameObject.Find("Drone3"));

		foreach (GameObject drone in drones) {
			moves.Add (drone.GetComponent<Movement> ());
		}
 
		ws_cur = new WebSocket ("ws://localhost:9000");
		ws_cur.OnMessage += (sender, e) => {
            if (e.IsText)
            {
				//Debug.Log(e.Data);
                if (!netControlled)
                {
                    netControlled = true;
                }
                string actions = e.Data.ToString();
				if (actions == "-1:-1:-1:-1") 
				{
					if (goals.Count != 0)
					{
						foreach (KeyValuePair<int, CollisionDetect> colPair in colDets)
						{
							CollisionDetect colDet = colPair.Value;
							colDet.dest = true;
						}
					}
				} 
				List<string> stringList = actions.Split(':').ToList();
                for (int i = 0; i < 4; i++)
                {
                    int action = int.Parse(stringList[i]);
                    if (action == 0) {
						moves[i].direction = dir0;
						//Debug.Log("yo");
                    }
                    else if (action == 1) {
						moves[i].direction = dir1;
						//Debug.Log("ya");
                    }
                    else if (action == 2) {
						moves[i].direction = dir2;
						//Debug.Log("ye");
                    }
                    else if (action == 3) {
						moves[i].direction = dir3;
						//Debug.Log("ying");
					} 
					moves[i].toSend = true;

                    //Debug.Log("Received action, " + e.Data.ToString());
                }
            }
		};
		ws_cur.Connect ();
		ws_cur.Send ("sunity:4");
	}
	
	// Update is called once per frame
	void Update () {
		if (netControlled && (Time.time - timeSinceSend) > 2) {
			SendData ();
		}
        bool send = true;
        foreach (GameObject drone in drones)
        {
            if(!drone.GetComponent<Movement>().toSend)
            {
                send = false;
            }
        }
        if (send)
        {
            SendData();
            foreach (GameObject drone in drones)
            {
                drone.GetComponent<Movement>().toSend = false;
            }
        }
	}

	string buildOutput() {
        string output = "";
        foreach (GameObject drone in drones)
        {
            output += round_dp(drone.transform.position.x).ToString() + ":";
            output += round_dp(drone.transform.position.z).ToString() + ":";
            output += round_dp(drone.GetComponent<Rigidbody>().velocity.x).ToString() + ":";
            output += round_dp(drone.GetComponent<Rigidbody>().velocity.z).ToString() + ":";
        }
        for (int i = 0; i < instantiateGoal.numGoals; i++)
        {
            if (goals.ContainsKey(i))
            {
                GameObject goal = goals[i];
                output += round_dp(goal.transform.position.x).ToString() + ":";
                output += round_dp(goal.transform.position.z).ToString() + ":";
            }
            else
            {
                //damping large value
                output += "2048:2048:";
            }
        }

		
        string succ = success.ToString();
        return output + succ;
	}

	float round_dp(float input){
		return Mathf.Round (input * 10f) / 10f;
	}

    public void SendData()
    {
        ws_cur.Send('d'+buildOutput());
        //Debug.Log("Sending Data, " + buildOutput());
        if (success > 0)
        {
            success = 0;
        }
        timeSinceSend = Time.time;
    }
}
