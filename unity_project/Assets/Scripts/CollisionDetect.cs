using UnityEngine;
using System.Collections;

public class CollisionDetect : MonoBehaviour {

    private GameObject controller;

    private DataTrack dataScript;

	public bool dest = false;

    public int id;

	// Use this for initialization
	void Start () {
        controller = GameObject.FindGameObjectWithTag("Controller");
        dataScript = controller.GetComponent<DataTrack>();
	}
	
	// Update is called once per frame
	void Update () {
		if (dest) {
            dataScript.goals.Remove(id);
			Destroy (gameObject);
		}
	}
    void OnTriggerEnter(Collider other)
    {
        if(other.gameObject.tag == "Drone")
        {
            dataScript.goals.Remove(id);
            dataScript.success += 1;
            Destroy(gameObject);
        }
    }
}
