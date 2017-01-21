using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class InstantiateGoal : MonoBehaviour {

    public GameObject goal;
    private float planeSize;
    private GameObject drone0;
    private GameObject drone1;
    private GameObject drone2;
    private GameObject drone3;
    private bool discrete;
    private float discreteMagnitude;

    public int numGoals;

    private DataTrack dataTrackScript;

    List<Vector3> occupiedLocations = new List<Vector3>();

    // Use this for initialization
    void Start () {
        dataTrackScript = GameObject.FindGameObjectWithTag("Controller").GetComponent<DataTrack>();
        drone0 = GameObject.Find("Drone0");
        drone1 = GameObject.Find("Drone1");
        drone2 = GameObject.Find("Drone2");
        drone3 = GameObject.Find("Drone3");
        planeSize = GameObject.Find("Ground").GetComponent<Collider>().bounds.size.x/2;
        discrete = dataTrackScript.discrete;
        discreteMagnitude = dataTrackScript.discreteMagnitude;
        CreateGoals();
	}
	
	// Update is called once per frame
	void Update () {
	    if (gameObject.transform.childCount == 0)
        {
            CreateGoals();
        }
	}

    void CreateGoals()
    {
        occupiedLocations.Clear();
        Vector3 drone0Location = drone0.transform.position;
        Vector3 drone1Location = drone1.transform.position;
        Vector3 drone2Location = drone2.transform.position;
        Vector3 drone3Location = drone3.transform.position;
        Vector3 spawnLocation = drone0Location;
        occupiedLocations.Add(drone0Location);
        occupiedLocations.Add(drone1Location);
        occupiedLocations.Add(drone2Location);
        occupiedLocations.Add(drone3Location);
        //Keep trying new locations until one is sufficiently far from the drone
        //Play with this value to make the game slightly harder or easier
        
        for (int i = 0; i < numGoals; i++)
        {
            bool canSpawn = false;
            while (!canSpawn)
            {
                if (discrete)
                {
                    spawnLocation = ChooseDiscreteLocation();
                }
                else
                {
                    spawnLocation = ChooseContinuousLocation();
                }
                canSpawn = CheckValidLocation(spawnLocation);
                //Debug.Log(canSpawn);
            }
            //Debug.Log(spawnLocation);
            occupiedLocations.Add(spawnLocation);
            GameObject goalClone = (GameObject)Instantiate(goal, spawnLocation, Quaternion.identity);
            goalClone.GetComponent<CollisionDetect>().id = i;
            dataTrackScript.goals.Add(i, goalClone);
            goalClone.transform.SetParent(gameObject.transform);
        }
    }

    private Vector3 ChooseDiscreteLocation()
    {
        int integerPlaneSize = (int)(planeSize/discreteMagnitude);
        int randx = Random.Range(-integerPlaneSize, integerPlaneSize);
        int randz = Random.Range(-integerPlaneSize, integerPlaneSize);
        return new Vector3(randx + (discreteMagnitude/2), 0.5f, randz + (discreteMagnitude / 2)) * discreteMagnitude;
    }

    private Vector3 ChooseContinuousLocation()
    {
        float randx = Random.Range(-planeSize + 1f, planeSize - 1f);
        float randz = Random.Range(-planeSize + 1f, planeSize - 1f);
        return new Vector3(randx, 0.5f, randz);
    }

    private bool CheckValidLocation(Vector3 spawnLoc)
    {
        bool canSpawn = true;
        foreach (var check in occupiedLocations)
        {
            if (Vector3.Distance(check, spawnLoc) < 1.5f)
            {
                canSpawn = false;
            }
        }
        return canSpawn;
    }
}
